"""
Admin routes for Ilsa (the admin).
Full CRUD on task templates, manual task generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from datetime import date

from app.database import get_session
from app.models import (
    TaskTemplateCreate, TaskTemplateRead, TaskTemplateUpdate,
    TaskRead
)
from app.services import task_service

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

@router.post("/generate/{target_date}", response_model=list[TaskRead])
def generate_tasks(target_date: date, session: Session = Depends(get_session)):
    """Manually generate tasks for a specific date from templates."""
    return task_service.generate_tasks_for_date(session, target_date)


@router.post("/generate/today", response_model=list[TaskRead])
def generate_todays_tasks(session: Session = Depends(get_session)):
    """Manually generate today's tasks from templates."""
    return task_service.generate_tasks_for_date(session, date.today())

