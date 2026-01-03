"""
Admin routes for Ilse (the admin).
Full CRUD on task templates, manual task generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from datetime import date
import logging

from app.database import get_session
from app.models import (
    TaskTemplateCreate, TaskTemplateRead, TaskTemplateUpdate,
    TaskRead, TaskCreate, Task
)
from app.services import task_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


# ============ Template Management ============

@router.get("/templates", response_model=list[TaskTemplateRead])
def list_templates(
    active_only: bool = False, 
    session: Session = Depends(get_session)
):
    """List all task templates."""
    return task_service.get_templates(session, active_only=active_only)


@router.post("/templates", response_model=TaskTemplateRead)
def create_template(
    template: TaskTemplateCreate, 
    session: Session = Depends(get_session)
):
    """Create a new task template."""
    return task_service.create_template(session, template)


@router.get("/templates/{template_id}", response_model=TaskTemplateRead)
def get_template(template_id: int, session: Session = Depends(get_session)):
    """Get a specific task template."""
    template = task_service.get_template(session, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.patch("/templates/{template_id}", response_model=TaskTemplateRead)
def update_template(
    template_id: int,
    updates: TaskTemplateUpdate,
    session: Session = Depends(get_session)
):
    """Update a task template."""
    template = task_service.update_template(session, template_id, updates)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.delete("/templates/{template_id}")
def delete_template(template_id: int, session: Session = Depends(get_session)):
    """Delete a task template."""
    if not task_service.delete_template(session, template_id):
        raise HTTPException(status_code=404, detail="Template not found")
    return {"ok": True}


# ============ Task Generation ============

@router.post("/generate/today", response_model=list[TaskRead])
def generate_todays_tasks(session: Session = Depends(get_session)):
    """Manually generate today's tasks from templates."""
    return task_service.generate_tasks_for_date(session, date.today())


@router.post("/generate/{target_date}", response_model=list[TaskRead])
def generate_tasks(target_date: date, session: Session = Depends(get_session)):
    """Manually generate tasks for a specific date from templates."""
    return task_service.generate_tasks_for_date(session, target_date)


# ============ Direct Task Creation ============

@router.post("/tasks", response_model=TaskRead)
def create_task(task_data: TaskCreate, session: Session = Depends(get_session)):
    """Create an ad-hoc task for a specific date."""
    task = Task(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        order=task_data.order,
        expected_minutes=task_data.expected_minutes,
        scheduled_date=task_data.scheduled_date,
        template_id=None,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, session: Session = Depends(get_session)):
    """
    Delete a task. 
    For template-based weekly tasks, removes that day from the template's weekdays.
    For template-based daily tasks, converts to weekly on remaining weekdays.
    """
    logger.info(f"Deleting task {task_id}")
    result = task_service.delete_task_with_template_update(session, task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True}


@router.post("/tasks/reorder")
def reorder_tasks(task_orders: list[dict], session: Session = Depends(get_session)):
    """
    Update order of multiple tasks. Expects [{id: 1, order: 0}, ...]
    For template-based tasks, also updates the template's order.
    """
    for item in task_orders:
        task_service.reorder_task(session, item["id"], item["order"])
    return {"ok": True}


@router.post("/tasks/{task_id}/move")
def move_task(task_id: int, target_date: date, order: int, session: Session = Depends(get_session)):
    """
    Move a task to a different date and/or order.
    For template-based tasks, updates the template's weekdays.
    
    Returns the task at target_date, or {"ok": True} if task was removed
    from source but target already had an instance (edge case).
    """
    logger.info(f"Moving task {task_id} to date={target_date}, order={order}")
    
    # Check if task exists before move
    from app.models import Task
    original_task = session.get(Task, task_id)
    if not original_task:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    
    result = task_service.move_task_to_date(session, task_id, target_date, order)
    
    if result:
        logger.info(f"Task moved successfully: id={result.id}, date={result.scheduled_date}")
        return result
    else:
        # Task was successfully processed (e.g., deleted from source when moving to existing day)
        # Try to find the task on target date
        target_tasks = task_service.get_tasks_for_date(session, target_date)
        for t in target_tasks:
            if original_task.template_id and t.template_id == original_task.template_id:
                logger.info(f"Returning existing task on target: id={t.id}")
                return t
        
        # Edge case: source was deleted, target might not have task yet (different week)
        logger.info(f"Move completed - source task deleted")
        return {"ok": True, "message": "Task removed from source date"}


@router.post("/snapshot/{target_date}")
def create_snapshot(target_date: date, session: Session = Depends(get_session)):
    """Create end-of-day snapshot for a date, preserving task states."""
    tasks = task_service.create_daily_snapshot(session, target_date)
    return {"ok": True, "snapshot_count": len(tasks)}


@router.post("/regenerate/{target_date}")
def regenerate_tasks_for_date(target_date: date, session: Session = Depends(get_session)):
    """Clear and regenerate tasks for a specific date from active templates."""
    logger.info(f"Regenerating tasks for {target_date}")
    tasks = task_service.regenerate_tasks_for_date(session, target_date)
    return tasks


@router.post("/regenerate-week")
def regenerate_week_tasks(session: Session = Depends(get_session)):
    """Clear and regenerate tasks for the entire current week."""
    from datetime import timedelta
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    
    all_tasks = []
    for i in range(7):
        day = monday + timedelta(days=i)
        logger.info(f"Regenerating tasks for {day}")
        tasks = task_service.regenerate_tasks_for_date(session, day)
        all_tasks.extend(tasks)
    
    return {"regenerated_count": len(all_tasks)}

