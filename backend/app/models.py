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


class RepeatType(str, Enum):
    NONE = "none"
    DAILY = "daily"      # All work days (Mon-Fri)
    WEEKLY = "weekly"    # Specific days of week
    MONTHLY = "monthly"  # Same day of month


# TaskTemplate: Defines recurring tasks (managed by Ilse)
class TaskTemplateBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.OPTIONAL
    repeat_type: RepeatType = Field(default=RepeatType.NONE)
    weekdays: str = Field(default="")  # Comma-separated: "0,2,4" for Mon,Wed,Fri
    order: int = Field(default=0)
    expected_minutes: int = Field(default=30)
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
    repeat_type: Optional[RepeatType] = None
    weekdays: Optional[str] = None
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
    is_snapshot: bool = Field(default=False)  # True = historical record, immutable
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    # Relationship back to template
    template: Optional[TaskTemplate] = Relationship(back_populates="tasks")


class RepeatInfo(SQLModel):
    """Nested info about repeat pattern for API responses."""
    type: RepeatType
    days: list[str] = []  # e.g. ["Mon", "Thu"]


class TaskRead(TaskBase):
    id: int
    template_id: Optional[int]
    is_snapshot: bool = False
    repeat_info: Optional[RepeatInfo] = None
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



