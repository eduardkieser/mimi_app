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


class TestDeleteTemplateTasks:
    """Tests for deleting template-based tasks."""
    
    def test_delete_template_task_prevents_regeneration(self, client, sample_template):
        """Deleting a template-based task should prevent it from regenerating."""
        # Generate task for Monday (2025-12-29)
        gen_response = client.post("/api/admin/generate/2025-12-29")
        assert gen_response.status_code == 200
        tasks = gen_response.json()
        assert len(tasks) == 1
        task_id = tasks[0]["id"]
        
        # Delete the task
        del_response = client.delete(f"/api/admin/tasks/{task_id}")
        assert del_response.status_code == 200
        
        # Try to get tasks for that date again - should NOT regenerate
        get_response = client.get("/api/tasks/date/2025-12-29")
        tasks_after = get_response.json()
        
        # The task should NOT have been regenerated
        assert len(tasks_after) == 0, "Template-based task was regenerated after deletion!"
    
    def test_delete_weekly_task_removes_day_from_template(self, client, sample_template):
        """Deleting a weekly task should remove that day from template's weekdays."""
        # Generate task for Monday (weekday 0)
        gen_response = client.post("/api/admin/generate/2025-12-29")
        assert gen_response.status_code == 200
        tasks = gen_response.json()
        task_id = tasks[0]["id"]
        
        # Delete the task
        del_response = client.delete(f"/api/admin/tasks/{task_id}")
        assert del_response.status_code == 200
        
        # Check template - Monday should be removed from weekdays
        template_response = client.get(f"/api/admin/templates/{sample_template.id}")
        template = template_response.json()
        
        # Original weekdays: "0,2,4" (Mon, Wed, Fri)
        # After delete: should be "2,4" (Wed, Fri)
        assert "0" not in template["weekdays"], "Monday was not removed from template weekdays!"
    
    def test_delete_daily_task_converts_to_weekly(self, client, sample_daily_template):
        """Deleting a daily task should convert template to weekly on remaining days."""
        # Generate task for Monday (2025-12-29, weekday 0)
        gen_response = client.post("/api/admin/generate/2025-12-29")
        assert gen_response.status_code == 200
        tasks = gen_response.json()
        
        # Find the daily task
        daily_task = [t for t in tasks if t["title"] == "Vacuum Living Room"][0]
        task_id = daily_task["id"]
        
        # Delete the task
        del_response = client.delete(f"/api/admin/tasks/{task_id}")
        assert del_response.status_code == 200
        
        # Check template - should be converted to weekly, excluding Monday
        template_response = client.get(f"/api/admin/templates/{sample_daily_template.id}")
        template = template_response.json()
        
        # Should now be WEEKLY instead of DAILY
        assert template["repeat_type"] == "weekly", "Template should be converted to weekly!"
        # Should have weekdays 1,2,3,4 (Tue, Wed, Thu, Fri) - Monday (0) excluded
        weekdays = set(template["weekdays"].split(","))
        assert "0" not in weekdays, "Monday should be excluded from weekdays!"
        assert weekdays == {"1", "2", "3", "4"}, f"Expected Tue-Fri, got {weekdays}"


class TestMoveTemplateTasks:
    """Tests for moving template-based tasks."""
    
    def test_move_weekly_task_updates_template_weekdays(self, client, sample_template):
        """Moving a weekly task should update the template's weekdays and persist."""
        # Generate task for Monday (2025-12-29, weekday 0)
        gen_response = client.post("/api/admin/generate/2025-12-29")
        assert gen_response.status_code == 200
        tasks = gen_response.json()
        task_id = tasks[0]["id"]
        
        # Move to Thursday (2026-01-01, weekday 3)
        move_response = client.post(
            f"/api/admin/tasks/{task_id}/move?target_date=2026-01-01&order=0"
        )
        assert move_response.status_code == 200
        
        # Check template weekdays - should now include Thursday, not Monday
        template_response = client.get(f"/api/admin/templates/{sample_template.id}")
        template = template_response.json()
        
        # Original: "0,2,4" (Mon, Wed, Fri)
        # After move: should be "2,3,4" (Wed, Thu, Fri)
        assert "3" in template["weekdays"], "Thursday was not added to template weekdays!"
        assert "0" not in template["weekdays"], "Monday was not removed from template weekdays!"
    
    def test_move_weekly_task_does_not_reappear_on_original_date(self, client, sample_template):
        """After moving a weekly task, it should not reappear on the original date."""
        # Generate task for Monday (2025-12-29)
        gen_response = client.post("/api/admin/generate/2025-12-29")
        assert gen_response.status_code == 200
        tasks = gen_response.json()
        task_id = tasks[0]["id"]
        
        # Move to Tuesday (2025-12-30, weekday 1)
        move_response = client.post(
            f"/api/admin/tasks/{task_id}/move?target_date=2025-12-30&order=0"
        )
        assert move_response.status_code == 200
        
        # Get tasks for original date (Monday) - should be empty
        mon_response = client.get("/api/tasks/date/2025-12-29")
        mon_tasks = mon_response.json()
        assert len(mon_tasks) == 0, "Task reappeared on original date after move!"
        
        # Get tasks for new date (Tuesday) - should have the task
        tue_response = client.get("/api/tasks/date/2025-12-30")
        tue_tasks = tue_response.json()
        assert len(tue_tasks) == 1, "Task was not on the target date!"


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

