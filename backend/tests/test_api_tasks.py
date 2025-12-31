"""
Tests for task API endpoints (Mimi's view).
"""
import pytest
from datetime import date


class TestHealthEndpoint:
    """Tests for the health check endpoint."""
    
    def test_health_returns_ok(self, client):
        """Health endpoint should return ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "Mimi.Today"


class TestGetTasks:
    """Tests for task retrieval endpoints."""
    
    def test_get_today_tasks_empty(self, client):
        """Should return empty list when no tasks exist."""
        response = client.get("/api/tasks/today")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_tasks_for_date(self, client, sample_task):
        """Should return tasks for a specific date."""
        today = date.today().isoformat()
        response = client.get(f"/api/tasks/date/{today}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Fix Door Handle"
    
    def test_get_tasks_includes_repeat_info(self, client, sample_template):
        """Tasks from templates should include repeat_info."""
        # Monday - matches the weekly template
        response = client.get("/api/tasks/date/2025-12-29")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["repeat_info"] is not None
        assert data[0]["repeat_info"]["type"] == "weekly"
    
    def test_get_tasks_for_future_date(self, client, sample_template):
        """Should generate tasks from templates for future dates."""
        # A Wednesday in the future
        response = client.get("/api/tasks/date/2026-01-07")
        
        assert response.status_code == 200
        data = response.json()
        # Should have task from weekly template (Wed is in weekdays)
        assert len(data) == 1


class TestCompleteTask:
    """Tests for task completion endpoints."""
    
    def test_complete_task(self, client, sample_task):
        """Should mark task as completed."""
        response = client.post(f"/api/tasks/{sample_task.id}/complete")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None
    
    def test_complete_nonexistent_task(self, client):
        """Should return 404 for nonexistent task."""
        response = client.post("/api/tasks/9999/complete")
        assert response.status_code == 404
    
    def test_uncomplete_task(self, client, sample_completed_task):
        """Should mark completed task as pending."""
        response = client.post(f"/api/tasks/{sample_completed_task.id}/uncomplete")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["completed_at"] is None


class TestUpdateTask:
    """Tests for task update endpoint."""
    
    def test_update_task_title(self, client, sample_task):
        """Should update task title."""
        response = client.patch(
            f"/api/tasks/{sample_task.id}",
            json={"title": "New Title"}
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "New Title"
    
    def test_update_task_priority(self, client, sample_task):
        """Should update task priority."""
        response = client.patch(
            f"/api/tasks/{sample_task.id}",
            json={"priority": "optional"}
        )
        
        assert response.status_code == 200
        assert response.json()["priority"] == "optional"


class TestTaskHistory:
    """Tests for task history endpoint."""
    
    def test_get_history(self, client, sample_task, sample_completed_task):
        """Should return task history grouped by date."""
        response = client.get("/api/tasks/history?days=7")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have today's date as a key
        today = date.today().isoformat()
        assert today in data
        assert len(data[today]) == 2

