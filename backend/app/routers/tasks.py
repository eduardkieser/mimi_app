"""
Task routes for Mimi (the cleaner).
GET today's tasks, mark complete/incomplete.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from datetime import date

from app.database import get_session
from app.models import TaskRead, TaskUpdate
from app.services import task_service

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/today", response_model=list[TaskRead])
def get_todays_tasks(session: Session = Depends(get_session)):
    """Get today's tasks, generating them from templates if needed."""
    # First try to generate (idempotent)
    task_service.generate_tasks_for_date(session, date.today())
    return task_service.get_todays_tasks(session)


@router.get("/date/{target_date}", response_model=list[TaskRead])
def get_tasks_for_date(target_date: date, session: Session = Depends(get_session)):
    """Get tasks for a specific date."""
    return task_service.get_tasks_for_date(session, target_date)


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete_task(task_id: int, session: Session = Depends(get_session)):
    """Mark a task as completed."""
    task = task_service.complete_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/uncomplete", response_model=TaskRead)
def uncomplete_task(task_id: int, session: Session = Depends(get_session)):
    """Mark a task as pending (undo completion)."""
    task = task_service.uncomplete_task(session, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


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
    return task


@router.get("/history")
def get_history(days: int = 7, session: Session = Depends(get_session)):
    """Get task completion history for the last N days."""
    history = task_service.get_recent_days(session, days)
    # Convert to JSON-serializable format
    return {
        str(d): [TaskRead.model_validate(t) for t in tasks]
        for d, tasks in history.items()
    }



