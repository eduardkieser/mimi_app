"""
Task routes for Mimi (the cleaner).
GET today's tasks, mark complete/incomplete.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from datetime import date

from app.database import get_session
from app.models import TaskRead, TaskUpdate, Task
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def task_to_read(task: Task, session: Session) -> TaskRead:
    """Convert Task to TaskRead with repeat_info populated."""
    repeat_info = None
    if task.template_id:
        template = task_service.get_template(session, task.template_id)
        if template:
            repeat_info = task_service.get_repeat_info(template)
    
    return TaskRead(
        id=task.id,
        title=task.title,
        description=task.description,
        priority=task.priority,
        order=task.order,
        expected_minutes=task.expected_minutes,
        scheduled_date=task.scheduled_date,
        status=task.status,
        template_id=task.template_id,
        is_snapshot=task.is_snapshot,
        repeat_info=repeat_info,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


@router.get("/today", response_model=list[TaskRead])
def get_todays_tasks(session: Session = Depends(get_session)):
    """Get today's tasks, generating them from templates if needed."""
    task_service.generate_tasks_for_date(session, date.today())
    tasks = task_service.get_todays_tasks(session)
    return [task_to_read(t, session) for t in tasks]


@router.get("/date/{target_date}", response_model=list[TaskRead])
def get_tasks_for_date(target_date: date, session: Session = Depends(get_session)):
    """Get tasks for a specific date, generating from templates if needed."""
    tasks = task_service.generate_tasks_for_date(session, target_date)
    return [task_to_read(t, session) for t in tasks]


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete_task(task_id: int, session: Session = Depends(get_session)):
    """Mark a task as completed."""
    task = task_service.complete_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_read(task, session)


@router.post("/{task_id}/uncomplete", response_model=TaskRead)
def uncomplete_task(task_id: int, session: Session = Depends(get_session)):
    """Mark a task as pending (undo completion)."""
    task = task_service.uncomplete_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_read(task, session)


@router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int, 
    updates: TaskUpdate, 
    session: Session = Depends(get_session)
):
    """Update a task's properties."""
    task = task_service.update_task(session, task_id, updates)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_read(task, session)


@router.get("/history")
def get_history(days: int = 7, session: Session = Depends(get_session)):
    """Get task completion history for the last N days."""
    history = task_service.get_recent_days(session, days)
    return {
        str(d): [task_to_read(t, session) for t in tasks]
        for d, tasks in history.items()
    }



