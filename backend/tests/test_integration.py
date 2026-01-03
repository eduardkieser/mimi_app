"""
Integration tests for Mimi.Today
Tests full workflows across API endpoints, simulating user interactions.
These tests verify edge cases documented in docs/EDGE_CASES.md
"""
import pytest
from datetime import date, timedelta
from httpx import Client, ASGITransport

from app.main import app
from app.database import engine, get_session
from app.models import TaskTemplate, Task, RepeatType, TaskPriority
from sqlmodel import Session, select, delete


class TestIntegrationBase:
    """Base class for integration tests with cleanup."""
    
    @pytest.fixture(autouse=True)
    def setup_and_cleanup(self, session):
        """Clean up before and after each test."""
        # Clean up before
        session.exec(delete(Task))
        session.exec(delete(TaskTemplate))
        session.commit()
        
        yield
        
        # Clean up after
        session.exec(delete(Task))
        session.exec(delete(TaskTemplate))
        session.commit()


class TestWeeklyTaskWorkflows(TestIntegrationBase):
    """Test workflows for weekly recurring tasks."""
    
    def test_create_weekly_task_and_view_on_multiple_days(self, client, session):
        """Create a weekly task (Mon, Wed, Fri) and verify it appears on those days."""
        # Create template
        response = client.post("/api/admin/templates", json={
            "title": "Weekly Standup",
            "priority": "optional",
            "repeat_type": "weekly",
            "weekdays": "0,2,4",  # Mon, Wed, Fri
            "order": 0,
            "expected_minutes": 15
        })
        assert response.status_code == 200
        template = response.json()
        assert template["repeat_type"] == "weekly"
        
        # Get current week's Monday
        today = date.today()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        wednesday = monday + timedelta(days=2)
        friday = monday + timedelta(days=4)
        tuesday = monday + timedelta(days=1)
        
        # Check Monday has task
        response = client.get(f"/api/tasks/date/{monday}")
        assert response.status_code == 200
        tasks = response.json()
        assert any(t["title"] == "Weekly Standup" for t in tasks)
        
        # Check Wednesday has task
        response = client.get(f"/api/tasks/date/{wednesday}")
        tasks = response.json()
        assert any(t["title"] == "Weekly Standup" for t in tasks)
        
        # Check Friday has task
        response = client.get(f"/api/tasks/date/{friday}")
        tasks = response.json()
        assert any(t["title"] == "Weekly Standup" for t in tasks)
        
        # Check Tuesday does NOT have task
        response = client.get(f"/api/tasks/date/{tuesday}")
        tasks = response.json()
        assert not any(t["title"] == "Weekly Standup" for t in tasks)
    
    def test_move_weekly_task_to_different_day(self, client, session):
        """Moving a weekly task updates template weekdays."""
        # Create Mon, Wed template
        response = client.post("/api/admin/templates", json={
            "title": "Team Sync",
            "priority": "optional",
            "repeat_type": "weekly",
            "weekdays": "0,2",  # Mon, Wed
            "order": 0,
            "expected_minutes": 30
        })
        template_id = response.json()["id"]
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        tuesday = monday + timedelta(days=1)
        
        # Get Monday's task
        response = client.get(f"/api/tasks/date/{monday}")
        tasks = response.json()
        monday_task = next(t for t in tasks if t["title"] == "Team Sync")
        
        # Move Monday's task to Tuesday
        response = client.post(
            f"/api/admin/tasks/{monday_task['id']}/move?target_date={tuesday}&order=0"
        )
        assert response.status_code == 200
        
        # Verify template now has Tue, Wed (not Mon)
        response = client.get(f"/api/admin/templates/{template_id}")
        template = response.json()
        weekdays = template["weekdays"].split(",")
        assert "0" not in weekdays, "Monday should be removed"
        assert "1" in weekdays, "Tuesday should be added"
        assert "2" in weekdays, "Wednesday should remain"
        
        # Verify Monday no longer has task
        response = client.get(f"/api/tasks/date/{monday}")
        tasks = response.json()
        assert not any(t["title"] == "Team Sync" for t in tasks)
        
        # Verify Tuesday now has task
        response = client.get(f"/api/tasks/date/{tuesday}")
        tasks = response.json()
        assert any(t["title"] == "Team Sync" for t in tasks)
    
    def test_move_weekly_task_to_existing_day(self, client, session):
        """Moving a weekly task to a day it already exists on = delete from source."""
        # Create Mon, Wed, Fri template
        response = client.post("/api/admin/templates", json={
            "title": "Recurring Check",
            "priority": "optional",
            "repeat_type": "weekly",
            "weekdays": "0,2,4",  # Mon, Wed, Fri
            "order": 0,
            "expected_minutes": 10
        })
        template_id = response.json()["id"]
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)
        
        # Get Monday's task
        response = client.get(f"/api/tasks/date/{monday}")
        tasks = response.json()
        monday_task = next(t for t in tasks if t["title"] == "Recurring Check")
        
        # Move Monday's task to Friday (already exists on Friday!)
        response = client.post(
            f"/api/admin/tasks/{monday_task['id']}/move?target_date={friday}&order=0"
        )
        assert response.status_code == 200
        
        # Verify template now has Wed, Fri only (Monday removed)
        response = client.get(f"/api/admin/templates/{template_id}")
        template = response.json()
        weekdays = set(template["weekdays"].split(","))
        assert "0" not in weekdays, "Monday should be removed"
        assert "2" in weekdays, "Wednesday should remain"
        assert "4" in weekdays, "Friday should remain"
        
        # Verify only one task on Friday (not duplicated)
        response = client.get(f"/api/tasks/date/{friday}")
        tasks = response.json()
        recurring_checks = [t for t in tasks if t["title"] == "Recurring Check"]
        assert len(recurring_checks) == 1, "Should have exactly one task, not duplicated"
    
    def test_delete_weekly_task_removes_from_weekdays(self, client, session):
        """Deleting a weekly task instance removes that day from template."""
        # Create Mon, Wed template
        response = client.post("/api/admin/templates", json={
            "title": "Delete Test",
            "priority": "optional",
            "repeat_type": "weekly",
            "weekdays": "0,2",  # Mon, Wed
            "order": 0,
            "expected_minutes": 20
        })
        template_id = response.json()["id"]
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        wednesday = monday + timedelta(days=2)
        
        # Get Monday's task
        response = client.get(f"/api/tasks/date/{monday}")
        tasks = response.json()
        monday_task = next(t for t in tasks if t["title"] == "Delete Test")
        
        # Delete Monday's task
        response = client.delete(f"/api/admin/tasks/{monday_task['id']}")
        assert response.status_code == 200
        
        # Verify template now only has Wednesday
        response = client.get(f"/api/admin/templates/{template_id}")
        template = response.json()
        assert template["weekdays"] == "2"
        
        # Verify Monday no longer has task (even after reload)
        response = client.get(f"/api/tasks/date/{monday}")
        tasks = response.json()
        assert not any(t["title"] == "Delete Test" for t in tasks)
        
        # Wednesday still has task
        response = client.get(f"/api/tasks/date/{wednesday}")
        tasks = response.json()
        assert any(t["title"] == "Delete Test" for t in tasks)


class TestDailyTaskWorkflows(TestIntegrationBase):
    """Test workflows for daily recurring tasks."""
    
    def test_create_daily_task_appears_all_weekdays(self, client, session):
        """Daily task appears Mon-Fri."""
        response = client.post("/api/admin/templates", json={
            "title": "Daily Cleanup",
            "priority": "optional",
            "repeat_type": "daily",
            "weekdays": "",
            "order": 0,
            "expected_minutes": 10
        })
        assert response.status_code == 200
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        # Check all weekdays
        for i in range(5):  # Mon-Fri
            day = monday + timedelta(days=i)
            response = client.get(f"/api/tasks/date/{day}")
            tasks = response.json()
            assert any(t["title"] == "Daily Cleanup" for t in tasks), f"Missing on day {i}"
        
        # Check weekend - should NOT have task
        saturday = monday + timedelta(days=5)
        response = client.get(f"/api/tasks/date/{saturday}")
        tasks = response.json()
        assert not any(t["title"] == "Daily Cleanup" for t in tasks)
    
    def test_delete_daily_task_converts_to_weekly(self, client, session):
        """Deleting a daily task converts template to weekly minus that day."""
        response = client.post("/api/admin/templates", json={
            "title": "Daily to Weekly",
            "priority": "optional",
            "repeat_type": "daily",
            "weekdays": "",
            "order": 0,
            "expected_minutes": 15
        })
        template_id = response.json()["id"]
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        wednesday = monday + timedelta(days=2)
        
        # Get Wednesday's task
        response = client.get(f"/api/tasks/date/{wednesday}")
        tasks = response.json()
        wed_task = next(t for t in tasks if t["title"] == "Daily to Weekly")
        
        # Delete Wednesday's task
        response = client.delete(f"/api/admin/tasks/{wed_task['id']}")
        assert response.status_code == 200
        
        # Verify template is now weekly, excluding Wednesday
        response = client.get(f"/api/admin/templates/{template_id}")
        template = response.json()
        assert template["repeat_type"] == "weekly"
        weekdays = set(template["weekdays"].split(","))
        assert "2" not in weekdays, "Wednesday should be excluded"
        assert weekdays == {"0", "1", "3", "4"}, f"Expected Mon,Tue,Thu,Fri, got {weekdays}"
        
        # Verify Wednesday no longer has task
        response = client.get(f"/api/tasks/date/{wednesday}")
        tasks = response.json()
        assert not any(t["title"] == "Daily to Weekly" for t in tasks)
    
    def test_move_daily_task_to_different_day(self, client, session):
        """Moving a daily task converts to weekly."""
        response = client.post("/api/admin/templates", json={
            "title": "Daily Move Test",
            "priority": "optional",
            "repeat_type": "daily",
            "weekdays": "",
            "order": 0,
            "expected_minutes": 20
        })
        template_id = response.json()["id"]
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        saturday = monday + timedelta(days=5)  # Move to weekend!
        
        # Get Monday's task
        response = client.get(f"/api/tasks/date/{monday}")
        tasks = response.json()
        mon_task = next(t for t in tasks if t["title"] == "Daily Move Test")
        
        # Move to Saturday (weekend)
        response = client.post(
            f"/api/admin/tasks/{mon_task['id']}/move?target_date={saturday}&order=0"
        )
        assert response.status_code == 200
        
        # Verify template changed to weekly
        response = client.get(f"/api/admin/templates/{template_id}")
        template = response.json()
        assert template["repeat_type"] == "weekly"
        weekdays = set(template["weekdays"].split(","))
        assert "0" not in weekdays, "Monday should be removed"
        assert "5" in weekdays, "Saturday should be added"


class TestOneTimeTaskWorkflows(TestIntegrationBase):
    """Test workflows for one-time (non-recurring) tasks."""
    
    def test_create_and_move_one_time_task(self, client, session):
        """One-time task can be moved freely."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Create one-time task for today
        response = client.post("/api/admin/tasks", json={
            "title": "One Time Task",
            "priority": "optional",
            "scheduled_date": str(today),
            "order": 0,
            "expected_minutes": 30
        })
        assert response.status_code == 200
        task_id = response.json()["id"]
        
        # Verify it exists today
        response = client.get(f"/api/tasks/date/{today}")
        tasks = response.json()
        assert any(t["title"] == "One Time Task" for t in tasks)
        
        # Move to tomorrow
        response = client.post(
            f"/api/admin/tasks/{task_id}/move?target_date={tomorrow}&order=0"
        )
        assert response.status_code == 200
        
        # Verify moved
        response = client.get(f"/api/tasks/date/{today}")
        tasks = response.json()
        assert not any(t["title"] == "One Time Task" for t in tasks)
        
        response = client.get(f"/api/tasks/date/{tomorrow}")
        tasks = response.json()
        assert any(t["title"] == "One Time Task" for t in tasks)
    
    def test_delete_one_time_task(self, client, session):
        """Deleting one-time task removes it permanently."""
        today = date.today()
        
        response = client.post("/api/admin/tasks", json={
            "title": "Delete Me",
            "priority": "optional",
            "scheduled_date": str(today),
            "order": 0,
            "expected_minutes": 10
        })
        task_id = response.json()["id"]
        
        # Delete
        response = client.delete(f"/api/admin/tasks/{task_id}")
        assert response.status_code == 200
        
        # Verify gone
        response = client.get(f"/api/tasks/date/{today}")
        tasks = response.json()
        assert not any(t["title"] == "Delete Me" for t in tasks)


class TestTaskCompletionWorkflows(TestIntegrationBase):
    """Test task completion from Mimi client perspective."""
    
    def test_complete_and_uncomplete_task(self, client, session):
        """Tasks can be completed and uncompleted."""
        today = date.today()
        
        response = client.post("/api/admin/tasks", json={
            "title": "Complete Test",
            "priority": "optional",
            "scheduled_date": str(today),
            "order": 0,
            "expected_minutes": 15
        })
        task_id = response.json()["id"]
        
        # Complete
        response = client.post(f"/api/tasks/{task_id}/complete")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "completed"
        
        # Verify status
        response = client.get(f"/api/tasks/date/{today}")
        tasks = response.json()
        task = next(t for t in tasks if t["id"] == task_id)
        assert task["status"] == "completed"
        
        # Uncomplete
        response = client.post(f"/api/tasks/{task_id}/uncomplete")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "pending"


class TestReorderingWorkflows(TestIntegrationBase):
    """Test task reordering."""
    
    def test_reorder_tasks_same_day(self, client, session):
        """Tasks can be reordered within same day."""
        today = date.today()
        
        # Create 3 tasks
        for i, title in enumerate(["First", "Second", "Third"]):
            client.post("/api/admin/tasks", json={
                "title": title,
                "priority": "optional",
                "scheduled_date": str(today),
                "order": i,
                "expected_minutes": 10
            })
        
        # Get tasks
        response = client.get(f"/api/tasks/date/{today}")
        tasks = response.json()
        assert [t["title"] for t in sorted(tasks, key=lambda x: x["order"])] == ["First", "Second", "Third"]
        
        # Reorder: Third -> First -> Second
        task_ids = {t["title"]: t["id"] for t in tasks}
        reorders = [
            {"id": task_ids["Third"], "order": 0},
            {"id": task_ids["First"], "order": 1},
            {"id": task_ids["Second"], "order": 2}
        ]
        
        response = client.post("/api/admin/tasks/reorder", json=reorders)
        assert response.status_code == 200
        
        # Verify new order
        response = client.get(f"/api/tasks/date/{today}")
        tasks = response.json()
        assert [t["title"] for t in sorted(tasks, key=lambda x: x["order"])] == ["Third", "First", "Second"]


class TestEdgeCases(TestIntegrationBase):
    """Test specific edge cases from EDGE_CASES.md"""
    
    def test_task_generation_idempotency(self, client, session):
        """Multiple requests to same date don't duplicate tasks."""
        response = client.post("/api/admin/templates", json={
            "title": "Idempotent Task",
            "priority": "optional",
            "repeat_type": "daily",
            "weekdays": "",
            "order": 0,
            "expected_minutes": 10
        })
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        # Request same date multiple times
        for _ in range(5):
            response = client.get(f"/api/tasks/date/{monday}")
            tasks = response.json()
        
        # Should have exactly one task
        idempotent_tasks = [t for t in tasks if t["title"] == "Idempotent Task"]
        assert len(idempotent_tasks) == 1
    
    def test_delete_last_weekday_deactivates_template(self, client, session):
        """Deleting the last remaining weekday deactivates the template."""
        response = client.post("/api/admin/templates", json={
            "title": "Single Day",
            "priority": "optional",
            "repeat_type": "weekly",
            "weekdays": "0",  # Only Monday
            "order": 0,
            "expected_minutes": 10
        })
        template_id = response.json()["id"]
        
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        
        # Get Monday's task
        response = client.get(f"/api/tasks/date/{monday}")
        tasks = response.json()
        task = next(t for t in tasks if t["title"] == "Single Day")
        
        # Delete it
        response = client.delete(f"/api/admin/tasks/{task['id']}")
        assert response.status_code == 200
        
        # Template should be deactivated
        response = client.get(f"/api/admin/templates/{template_id}")
        template = response.json()
        assert template["is_active"] == False

