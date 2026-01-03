from sqlmodel import Session, select
from datetime import date, datetime
import logging
from app.models import (
    Task, TaskTemplate, TaskStatus, TaskPriority, RepeatType,
    TaskTemplateCreate, TaskTemplateUpdate, TaskUpdate, RepeatInfo
)

logger = logging.getLogger(__name__)

# Day name mapping
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def get_repeat_info(template: TaskTemplate) -> RepeatInfo | None:
    """Build RepeatInfo from a template."""
    if not template or template.repeat_type == RepeatType.NONE:
        return None
    
    days = []
    if template.repeat_type == RepeatType.WEEKLY and template.weekdays:
        day_indices = [int(d) for d in template.weekdays.split(",") if d]
        days = [DAY_NAMES[i] for i in day_indices if i < len(DAY_NAMES)]
    elif template.repeat_type == RepeatType.DAILY:
        days = DAY_NAMES[:5]  # Mon-Fri
    
    return RepeatInfo(type=template.repeat_type, days=days)


def template_matches_date(template: TaskTemplate, target_date: date) -> bool:
    """Check if a template should generate a task for the given date."""
    weekday = target_date.weekday()  # 0=Mon, 6=Sun
    
    if template.repeat_type == RepeatType.DAILY:
        # Daily = all weekdays (Mon-Fri)
        return weekday < 5
    
    elif template.repeat_type == RepeatType.WEEKLY:
        # Check if this weekday is in the template's weekdays list
        if not template.weekdays:
            return False
        weekday_list = [int(d) for d in template.weekdays.split(",") if d]
        return weekday in weekday_list
    
    elif template.repeat_type == RepeatType.MONTHLY:
        # Same day of month as when template was created
        # For now, just use the day of month from created_at
        return target_date.day == template.created_at.day
    
    return False


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
    Generate tasks for a given date based on active templates.
    Idempotent - won't duplicate tasks from the same template.
    """
    # Get existing tasks for this date
    existing = get_tasks_for_date(session, target_date)
    existing_template_ids = {t.template_id for t in existing if t.template_id}
    
    # Get all active templates
    statement = (
        select(TaskTemplate)
        .where(TaskTemplate.is_active == True)
        .order_by(TaskTemplate.order)
    )
    templates = session.exec(statement).all()
    
    # Create tasks from matching templates that don't already exist
    new_tasks = []
    for template in templates:
        if template.id in existing_template_ids:
            continue  # Already have this task
        if not template_matches_date(template, target_date):
            continue  # Doesn't match this date
        
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
        new_tasks.append(task)
    
    if new_tasks:
        session.commit()
        for task in new_tasks:
            session.refresh(task)
    
    return existing + new_tasks


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


# ============ Template-Aware Task Operations ============

def reorder_task(session: Session, task_id: int, new_order: int) -> Task | None:
    """
    Reorder a task. If it's template-based, update the template's order.
    """
    task = session.get(Task, task_id)
    if not task:
        return None
    
    # Update task order
    task.order = new_order
    session.add(task)
    
    # If template-based, also update the template
    if task.template_id:
        template = session.get(TaskTemplate, task.template_id)
        if template:
            template.order = new_order
            template.updated_at = datetime.utcnow()
            session.add(template)
    
    session.commit()
    session.refresh(task)
    return task


def move_task_to_date(session: Session, task_id: int, target_date: date, new_order: int) -> Task | None:
    """
    Move a task to a different date. 
    For template-based tasks, update the template's weekdays.
    """
    logger.info(f"move_task_to_date: task_id={task_id}, target_date={target_date}, new_order={new_order}")
    task = session.get(Task, task_id)
    if not task:
        logger.warning(f"Task {task_id} not found")
        return None
    
    logger.info(f"Found task: id={task.id}, title={task.title}, template_id={task.template_id}, current_date={task.scheduled_date}")
    source_weekday = task.scheduled_date.weekday()
    target_weekday = target_date.weekday()
    
    # If template-based and weekly, update the template's weekdays
    if task.template_id:
        template = session.get(TaskTemplate, task.template_id)
        if template and template.repeat_type == RepeatType.WEEKLY:
            # Parse current weekdays
            current_days = set()
            if template.weekdays:
                current_days = {int(d) for d in template.weekdays.split(",") if d}
            
            # Check if target day already exists in template (edge case: moving to existing day)
            if target_weekday in current_days and source_weekday != target_weekday:
                # Target day already has this task - just remove from source day
                logger.info(f"Target weekday {target_weekday} already in template, just removing source {source_weekday}")
                current_days.discard(source_weekday)
                
                if current_days:
                    template.weekdays = ",".join(str(d) for d in sorted(current_days))
                else:
                    template.is_active = False
                    
                template.updated_at = datetime.utcnow()
                session.add(template)
                session.delete(task)
                session.commit()
                
                # Generate/get the task on target date
                target_tasks = generate_tasks_for_date(session, target_date)
                for t in target_tasks:
                    if t.template_id == template.id:
                        logger.info(f"Returning existing task on target date: id={t.id}")
                        return t
                
                # If we still can't find it, the target date might be outside the current week
                # Just return a success indicator
                logger.info(f"Target task for template {template.id} on {target_date} - source deleted successfully")
                # Create a dummy response - task was successfully moved (source deleted)
                # Return None and let the caller handle it
                return None
            
            # Normal case: remove source day, add target day
            current_days.discard(source_weekday)
            current_days.add(target_weekday)
            
            # Update template
            template.weekdays = ",".join(str(d) for d in sorted(current_days))
            template.order = new_order
            template.updated_at = datetime.utcnow()
            session.add(template)
            
            # Delete the old task instance (a new one will be generated for the new day)
            logger.info(f"Deleting old task {task.id} and generating new one for {target_date}")
            session.delete(task)
            session.commit()
            
            # Generate task for the new date
            tasks = generate_tasks_for_date(session, target_date)
            logger.info(f"Generated {len(tasks)} tasks for {target_date}: {[(t.id, t.title, t.template_id) for t in tasks]}")
            
            # Return the newly generated task
            for t in tasks:
                if t.template_id == template.id:
                    logger.info(f"Returning newly generated task: id={t.id}, date={t.scheduled_date}")
                    return t
            
            logger.warning(f"Could not find generated task for template {template.id} on {target_date}")
            return None
        
        elif template and template.repeat_type == RepeatType.DAILY:
            if source_weekday == target_weekday:
                # Same day, just reorder
                template.order = new_order
                template.updated_at = datetime.utcnow()
                session.add(template)
                task.order = new_order
                session.add(task)
                session.commit()
                session.refresh(task)
                return task
            else:
                # Moving to different day - convert daily to weekly excluding source day
                logger.info(f"Converting daily template {template.id} to weekly, moving from weekday {source_weekday} to {target_weekday}")
                remaining_days = {d for d in range(5) if d != source_weekday}
                remaining_days.add(target_weekday)  # Add target day
                
                template.repeat_type = RepeatType.WEEKLY
                template.weekdays = ",".join(str(d) for d in sorted(remaining_days))
                template.order = new_order
                template.updated_at = datetime.utcnow()
                session.add(template)
                
                # Delete old task, generate new one
                logger.info(f"Deleting old task {task.id} and generating new one for {target_date}")
                session.delete(task)
                session.commit()
                
                # Generate task for the new date
                tasks = generate_tasks_for_date(session, target_date)
                logger.info(f"Generated {len(tasks)} tasks for {target_date}")
                
                for t in tasks:
                    if t.template_id == template.id:
                        logger.info(f"Returning newly generated task: id={t.id}, date={t.scheduled_date}")
                        return t
                
                logger.warning(f"Could not find generated task for template {template.id} on {target_date}")
                return None
    
    # Non-template task or monthly: just update the task directly
    task.scheduled_date = target_date
    task.order = new_order
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def delete_task_or_template(session: Session, task_id: int, delete_all_occurrences: bool = False) -> bool:
    """
    Delete a task. If delete_all_occurrences is True and task is template-based,
    deactivate the template.
    """
    task = session.get(Task, task_id)
    if not task:
        return False
    
    if delete_all_occurrences and task.template_id:
        template = session.get(TaskTemplate, task.template_id)
        if template:
            template.is_active = False
            template.updated_at = datetime.utcnow()
            session.add(template)
    
    session.delete(task)
    session.commit()
    return True


def delete_task_with_template_update(session: Session, task_id: int) -> bool:
    """
    Delete a task and update the template to prevent regeneration.
    - For weekly templates: removes the task's weekday from template weekdays
    - For daily templates: deactivates the template
    - For one-time/monthly or non-template tasks: just deletes the task
    """
    task = session.get(Task, task_id)
    if not task:
        return False
    
    if task.template_id:
        template = session.get(TaskTemplate, task.template_id)
        if template:
            if template.repeat_type == RepeatType.WEEKLY:
                # Remove this weekday from template
                task_weekday = task.scheduled_date.weekday()
                if template.weekdays:
                    current_days = {int(d) for d in template.weekdays.split(",") if d}
                    current_days.discard(task_weekday)
                    
                    if current_days:
                        template.weekdays = ",".join(str(d) for d in sorted(current_days))
                    else:
                        # No days left, deactivate template
                        template.is_active = False
                    
                    template.updated_at = datetime.utcnow()
                    session.add(template)
            
            elif template.repeat_type == RepeatType.DAILY:
                # Convert daily to weekly, excluding the deleted day
                task_weekday = task.scheduled_date.weekday()
                # Daily means Mon-Fri (0-4), so remaining days are all weekdays except deleted one
                remaining_days = {d for d in range(5) if d != task_weekday}
                
                if remaining_days:
                    template.repeat_type = RepeatType.WEEKLY
                    template.weekdays = ",".join(str(d) for d in sorted(remaining_days))
                    logger.info(f"Converted daily template {template.id} to weekly on days: {template.weekdays}")
                else:
                    # Only had one weekday somehow, deactivate
                    template.is_active = False
                
                template.updated_at = datetime.utcnow()
                session.add(template)
            
            # For monthly or none, just delete the task (template stays)
    
    session.delete(task)
    session.commit()
    return True


# ============ End of Day Snapshot ============

def create_daily_snapshot(session: Session, target_date: date) -> list[Task]:
    """
    Create permanent snapshots of all tasks for a given date.
    Call this at end of day to preserve history.
    """
    # Get all tasks for this date
    tasks = get_tasks_for_date(session, target_date)
    
    # Mark all template-generated tasks as snapshots
    for task in tasks:
        if task.template_id and not task.is_snapshot:
            task.is_snapshot = True
            session.add(task)
    
    session.commit()
    return tasks


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



