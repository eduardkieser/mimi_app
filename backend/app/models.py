from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, date
from typing import Optional
from enum import Enum


class TaskPriority(str, Enum):
    REQUIRED = "required"  # Red -> Green
    OPTIONAL = "optional"  # Yellow -> Green


class TaskStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Weekday(str, Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


# TaskTemplate: Defines recurring tasks (managed by Ilsa)
class TaskTemplateBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.OPTIONAL  # Optional by default
    is_recurring: bool = Field(default=True)  # Repeat every week
    default_weekday: Weekday = Weekday.TUESDAY
    order: int = Field(default=0)  # Display order
    expected_minutes: int = Field(default=30)  # Time estimate in minutes
    is_active: bool = Field(default=True)


class TaskTemplate(TaskTemplateBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationship to generated tasks
    tasks: list["Task"] = Relationship(back_populates="template")


class TaskTemplateCreate(TaskTemplateBase):
    pass


class TaskTemplateRead(TaskTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime


class TaskTemplateUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    is_recurring: Optional[bool] = None
    default_weekday: Optional[Weekday] = None
    order: Optional[int] = None
    expected_minutes: Optional[int] = None
    is_active: Optional[bool] = None


# Task: Daily instance of a task (what Mimi sees and completes)
class TaskBase(SQLModel):
    title: str
    description: Optional[str] = None
    priority: TaskPriority
    order: int = Field(default=0)
    expected_minutes: int = Field(default=30)
    scheduled_date: date = Field(index=True)
    status: TaskStatus = Field(default=TaskStatus.PENDING)


class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    template_id: Optional[int] = Field(default=None, foreign_key="tasktemplate.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Relationship back to template
    template: Optional[TaskTemplate] = Relationship(back_populates="tasks")


class TaskRead(TaskBase):
    id: int
    template_id: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]


class TaskUpdate(SQLModel):
    status: Optional[TaskStatus] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    order: Optional[int] = None
    expected_minutes: Optional[int] = None


class TaskCreate(SQLModel):
    """For creating ad-hoc tasks directly (not from template)."""
    title: str
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.OPTIONAL
    order: int = 0
    expected_minutes: int = 30
    scheduled_date: date



