"""
Pytest fixtures for Mimi.Today tests.
Provides test database, session, and HTTP client.
"""
import pytest
from datetime import date
from sqlmodel import SQLModel, Session, create_engine
from starlette.testclient import TestClient

from app.main import app
from app.database import get_session
from app.models import Task, TaskTemplate, TaskPriority, TaskStatus, RepeatType


# Test database - file-based SQLite for shared access between session and client
TEST_DATABASE_URL = "sqlite:///./test_mimi.db"


@pytest.fixture(name="engine", scope="function")
def engine_fixture():
    """Create a fresh database for each test."""
    import os
    # Remove old test db if exists
    if os.path.exists("test_mimi.db"):
        os.remove("test_mimi.db")
    
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    
    # Cleanup
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
    if os.path.exists("test_mimi.db"):
        os.remove("test_mimi.db")


@pytest.fixture(name="session")
def session_fixture(engine):
    """Create a database session for testing."""
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(engine, session):
    """Create a test client with the test database."""
    def get_test_session():
        # Use the same engine for the test client
        with Session(engine) as s:
            yield s
    
    app.dependency_overrides[get_session] = get_test_session
    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()


# ============ Sample Data Fixtures ============

@pytest.fixture
def sample_template(session) -> TaskTemplate:
    """Create a sample weekly task template."""
    template = TaskTemplate(
        title="Clean Kitchen",
        description="Weekly kitchen cleaning",
        priority=TaskPriority.REQUIRED,
        repeat_type=RepeatType.WEEKLY,
        weekdays="0,2,4",  # Mon, Wed, Fri
        order=0,
        expected_minutes=45,
        is_active=True,
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


@pytest.fixture
def sample_daily_template(session) -> TaskTemplate:
    """Create a sample daily task template."""
    template = TaskTemplate(
        title="Vacuum Living Room",
        description="Daily vacuuming",
        priority=TaskPriority.OPTIONAL,
        repeat_type=RepeatType.DAILY,
        weekdays="",
        order=1,
        expected_minutes=20,
        is_active=True,
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    return template


@pytest.fixture
def sample_task(session) -> Task:
    """Create a sample one-off task."""
    task = Task(
        title="Fix Door Handle",
        description="The handle is loose",
        priority=TaskPriority.REQUIRED,
        order=0,
        expected_minutes=15,
        scheduled_date=date.today(),
        status=TaskStatus.PENDING,
        template_id=None,
        is_snapshot=False,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


@pytest.fixture
def sample_completed_task(session) -> Task:
    """Create a sample completed task."""
    from datetime import datetime
    task = Task(
        title="Water Plants",
        priority=TaskPriority.OPTIONAL,
        order=1,
        expected_minutes=10,
        scheduled_date=date.today(),
        status=TaskStatus.COMPLETED,
        completed_at=datetime.utcnow(),
        template_id=None,
        is_snapshot=False,
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    return task

