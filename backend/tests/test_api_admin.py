"""
Tests for admin API endpoints (Ilse's panel).
"""
import pytest
from datetime import date


class TestTemplateEndpoints:
    """Tests for template CRUD endpoints."""
    
    def test_list_templates_empty(self, client):
        """Should return empty list when no templates exist."""
        response = client.get("/api/admin/templates")
        assert response.status_code == 200
        assert response.json() == []
    
    def test_list_templates(self, client, sample_template, sample_daily_template):
        """Should return all templates."""
        response = client.get("/api/admin/templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_create_template(self, client):
        """Should create a new template."""
        response = client.post(
            "/api/admin/templates",
            json={
                "title": "New Template",
                "priority": "required",
                "repeat_type": "weekly",
                "weekdays": "0,4",
                "order": 0,
                "expected_minutes": 30,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Template"
        assert data["weekdays"] == "0,4"
        assert data["is_active"] is True
    
    def test_get_template(self, client, sample_template):
        """Should return a specific template."""
        response = client.get(f"/api/admin/templates/{sample_template.id}")
        
        assert response.status_code == 200
        assert response.json()["title"] == "Clean Kitchen"
    
    def test_get_nonexistent_template(self, client):
        """Should return 404 for nonexistent template."""
        response = client.get("/api/admin/templates/9999")
        assert response.status_code == 404
    
    def test_update_template(self, client, sample_template):
        """Should update a template."""
        response = client.patch(
            f"/api/admin/templates/{sample_template.id}",
            json={"title": "Updated Kitchen Cleaning"}
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Kitchen Cleaning"
    
    def test_delete_template(self, client, sample_template):
        """Should delete a template."""
        response = client.delete(f"/api/admin/templates/{sample_template.id}")
        
        assert response.status_code == 200
        assert response.json()["ok"] is True
        
        # Verify it's gone
        response = client.get(f"/api/admin/templates/{sample_template.id}")
        assert response.status_code == 404


class TestTaskEndpoints:
    """Tests for direct task creation endpoints."""
    
    def test_create_task(self, client):
        """Should create an ad-hoc task."""
        response = client.post(
            "/api/admin/tasks",
            json={
                "title": "Ad-hoc Task",
                "priority": "optional",
                "order": 0,
                "expected_minutes": 20,
                "scheduled_date": "2025-12-31",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Ad-hoc Task"
        assert data["template_id"] is None
        assert data["scheduled_date"] == "2025-12-31"
    
    def test_delete_task(self, client, sample_task):
        """Should delete a task."""
        response = client.delete(f"/api/admin/tasks/{sample_task.id}")
        
        assert response.status_code == 200
        assert response.json()["ok"] is True


class TestTaskReordering:
    """Tests for task reordering endpoints."""
    
    def test_reorder_tasks(self, client, sample_task, sample_completed_task):
        """Should reorder multiple tasks."""
        response = client.post(
            "/api/admin/tasks/reorder",
            json=[
                {"id": sample_task.id, "order": 5},
                {"id": sample_completed_task.id, "order": 3},
            ]
        )
        
        assert response.status_code == 200
        assert response.json()["ok"] is True
        
        # Verify order changed
        today = date.today().isoformat()
        tasks_response = client.get(f"/api/tasks/date/{today}")
        tasks = tasks_response.json()
        
        task1 = next(t for t in tasks if t["id"] == sample_task.id)
        task2 = next(t for t in tasks if t["id"] == sample_completed_task.id)
        
        assert task1["order"] == 5
        assert task2["order"] == 3


class TestTaskMoving:
    """Tests for moving tasks between days."""
    
    def test_move_task_to_different_date(self, client, sample_task):
        """Should move a one-off task to a different date."""
        new_date = "2026-01-15"
        response = client.post(
            f"/api/admin/tasks/{sample_task.id}/move?target_date={new_date}&order=0"
        )
        
        assert response.status_code == 200
        assert response.json()["scheduled_date"] == new_date
    
    def test_move_nonexistent_task(self, client):
        """Should return 404 for nonexistent task."""
        response = client.post(
            "/api/admin/tasks/9999/move?target_date=2026-01-15&order=0"
        )
        assert response.status_code == 404


class TestTaskGeneration:
    """Tests for task generation endpoints."""
    
    def test_generate_tasks_for_date(self, client, sample_template):
        """Should generate tasks from templates."""
        # Monday - matches weekly template
        response = client.post("/api/admin/generate/2025-12-29")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Clean Kitchen"
    
    def test_generate_today_tasks(self, client, sample_daily_template):
        """Should generate today's tasks."""
        response = client.post("/api/admin/generate/today")
        
        assert response.status_code == 200
        # Result depends on what day it is


class TestSnapshot:
    """Tests for end-of-day snapshot."""
    
    def test_create_snapshot(self, client, sample_task):
        """Should create snapshot for a date."""
        today = date.today().isoformat()
        response = client.post(f"/api/admin/snapshot/{today}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["snapshot_count"] == 1


class TestPageEndpoints:
    """Tests for HTML page endpoints."""
    
    def test_mimi_page_loads(self, client):
        """Mimi's page should load."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Mimi.Today" in response.text
    
    def test_admin_page_loads(self, client):
        """Admin page should load."""
        response = client.get("/admin")
        assert response.status_code == 200
        assert "Ilse.Admin" in response.text

