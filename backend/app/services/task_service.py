from sqlmodel import Session, select
from datetime import date, datetime
from app.models import (
    Task, TaskTemplate, TaskStatus, TaskPriority, Weekday,
    TaskTemplateCreate, TaskTemplateUpdate, TaskUpdate
)


WEEKDAY_MAP = {
    Weekday.MONDAY: 0,
    Weekday.TUESDAY: 1,
    Weekday.WEDNESDAY: 2,
    Weekday.THURSDAY: 3,
    Weekday.FRIDAY: 4,
    Weekday.SATURDAY: 5,
    Weekday.SUNDAY: 6,
}


def get_weekday_enum(d: date) -> Weekday:
    """Convert a date to its Weekday enum."""
    weekday_num = d.weekday()
    for wd, num in WEEKDAY_MAP.items():
        if num == weekday_num:
            return wd
    return Weekday.MONDAY


# ============ Task Template Operations (Admin) ============

def create_template(session: Session, template: TaskTemplateCreate) -> TaskTemplate:
    db_template = TaskTemplate.model_validate(template)
    session.add(db_template)
    session.commit()
    session.refresh(db_template)
    return db_template


def get_templates(session: Session, active_only: bool = True) -> list[TaskTemplate]:
    statement = select(TaskTemplate)
    if active_only:
        statement = statement.where(TaskTemplate.is_active == True)
    statement = statement.order_by(TaskTemplate.order)
    return session.exec(statement).all()


def get_template(session: Session, template_id: int) -> TaskTemplate | None:
    return session.get(TaskTemplate, template_id)


def update_template(
    session: Session, template_id: int, updates: TaskTemplateUpdate
) -> TaskTemplate | None:
    template = session.get(TaskTemplate, template_id)
    if not template:
        return None
    
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    
    template.updated_at = datetime.utcnow()
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


def delete_template(session: Session, template_id: int) -> bool:
    template = session.get(TaskTemplate, template_id)
    if not template:
        return False
    session.delete(template)
    session.commit()
    return True


# ============ Task Operations (Mimi) ============

def get_tasks_for_date(session: Session, target_date: date) -> list[Task]:
    """Get all tasks for a specific date, ordered by priority then order."""
    statement = (
        select(Task)
        .where(Task.scheduled_date == target_date)
        .order_by(Task.priority, Task.order)
    )
    return session.exec(statement).all()


def get_todays_tasks(session: Session) -> list[Task]:
    """Get today's tasks."""
    return get_tasks_for_date(session, date.today())


def generate_tasks_for_date(session: Session, target_date: date) -> list[Task]:
    """
    Generate tasks for a given date based on active templates 
    that match the weekday. Idempotent - won't duplicate.
    """
    # Check if tasks already exist for this date
    existing = get_tasks_for_date(session, target_date)
    if existing:
        return existing
    
    # Get templates for this weekday
    target_weekday = get_weekday_enum(target_date)
    statement = (
        select(TaskTemplate)
        .where(TaskTemplate.is_active == True)
        .where(TaskTemplate.default_weekday == target_weekday)
        .order_by(TaskTemplate.order)
    )
    templates = session.exec(statement).all()
    
    # Create tasks from templates
    tasks = []
    for template in templates:
        task = Task(
            title=template.title,
            description=template.description,
            priority=template.priority,
            order=template.order,
            expected_minutes=template.expected_minutes,
            scheduled_date=target_date,
            template_id=template.id,
        )
        session.add(task)
        tasks.append(task)
    
    session.commit()
    for task in tasks:
        session.refresh(task)
    
    return tasks


def complete_task(session: Session, task_id: int) -> Task | None:
    """Mark a task as completed."""
    task = session.get(Task, task_id)
    if not task:
        return None
    
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def uncomplete_task(session: Session, task_id: int) -> Task | None:
    """Mark a task as pending (undo completion)."""
    task = session.get(Task, task_id)
    if not task:
        return None
    
    task.status = TaskStatus.PENDING
    task.completed_at = None
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def update_task(session: Session, task_id: int, updates: TaskUpdate) -> Task | None:
    """Update a task's properties."""
    task = session.get(Task, task_id)
    if not task:
        return None
    
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    
    # If status changed to completed, set completed_at
    if updates.status == TaskStatus.COMPLETED and task.completed_at is None:
        task.completed_at = datetime.utcnow()
    elif updates.status == TaskStatus.PENDING:
        task.completed_at = None
    
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def get_task(session: Session, task_id: int) -> Task | None:
    return session.get(Task, task_id)


# ============ History Operations ============

def get_recent_days(session: Session, days: int = 7) -> dict[date, list[Task]]:
    """Get tasks grouped by date for the last N days."""
    from datetime import timedelta
    
    today = date.today()
    result = {}
    
    for i in range(days):
        d = today - timedelta(days=i)
        result[d] = get_tasks_for_date(session, d)
    
    return result



