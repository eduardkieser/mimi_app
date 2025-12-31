"""
Tests for task_service.py - core business logic.
"""
import pytest
from datetime import date, timedelta

from app.services import task_service
from app.models import (
    Task, TaskTemplate, TaskPriority, TaskStatus, RepeatType,
    TaskTemplateCreate, TaskTemplateUpdate, TaskUpdate
)


class TestTemplateMatching:
    """Tests for template_matches_date logic."""
    
    def test_daily_matches_weekdays(self, session, sample_daily_template):
        """Daily templates should match Mon-Fri."""
        # Monday
        monday = date(2025, 12, 29)
        assert task_service.template_matches_date(sample_daily_template, monday) is True
        
        # Friday
        friday = date(2026, 1, 2)
        assert task_service.template_matches_date(sample_daily_template, friday) is True
    
    def test_daily_does_not_match_weekends(self, session, sample_daily_template):
        """Daily templates should not match Sat/Sun."""
        saturday = date(2025, 12, 27)
        sunday = date(2025, 12, 28)
        
        assert task_service.template_matches_date(sample_daily_template, saturday) is False
        assert task_service.template_matches_date(sample_daily_template, sunday) is False
    
    def test_weekly_matches_specified_days(self, session, sample_template):
        """Weekly templates match only specified weekdays."""
        # sample_template has weekdays="0,2,4" (Mon, Wed, Fri)
        monday = date(2025, 12, 29)  # Monday
        tuesday = date(2025, 12, 30)  # Tuesday
        wednesday = date(2025, 12, 31)  # Wednesday
        
        assert task_service.template_matches_date(sample_template, monday) is True
        assert task_service.template_matches_date(sample_template, tuesday) is False
        assert task_service.template_matches_date(sample_template, wednesday) is True


class TestTemplateOperations:
    """Tests for template CRUD operations."""
    
    def test_create_template(self, session):
        """Test creating a new template."""
        template_data = TaskTemplateCreate(
            title="Test Template",
            priority=TaskPriority.OPTIONAL,
            repeat_type=RepeatType.WEEKLY,
            weekdays="1,3",  # Tue, Thu
            order=0,
            expected_minutes=30,
        )
        template = task_service.create_template(session, template_data)
        
        assert template.id is not None
        assert template.title == "Test Template"
        assert template.weekdays == "1,3"
        assert template.is_active is True
    
    def test_get_templates(self, session, sample_template, sample_daily_template):
        """Test retrieving templates."""
        templates = task_service.get_templates(session)
        assert len(templates) == 2
    
    def test_get_templates_active_only(self, session, sample_template):
        """Test filtering to active templates only."""
        # Deactivate the template
        sample_template.is_active = False
        session.add(sample_template)
        session.commit()
        
        templates = task_service.get_templates(session, active_only=True)
        assert len(templates) == 0
    
    def test_update_template(self, session, sample_template):
        """Test updating a template."""
        updates = TaskTemplateUpdate(title="Updated Title", expected_minutes=60)
        updated = task_service.update_template(session, sample_template.id, updates)
        
        assert updated.title == "Updated Title"
        assert updated.expected_minutes == 60
        assert updated.priority == TaskPriority.REQUIRED  # Unchanged
    
    def test_delete_template(self, session, sample_template):
        """Test deleting a template."""
        template_id = sample_template.id
        result = task_service.delete_template(session, template_id)
        
        assert result is True
        assert task_service.get_template(session, template_id) is None


class TestTaskGeneration:
    """Tests for task generation from templates."""
    
    def test_generate_creates_tasks_from_templates(self, session, sample_template):
        """Generate tasks should create tasks from matching templates."""
        # Monday - matches sample_template (weekdays="0,2,4")
        monday = date(2025, 12, 29)
        tasks = task_service.generate_tasks_for_date(session, monday)
        
        assert len(tasks) == 1
        assert tasks[0].title == "Clean Kitchen"
        assert tasks[0].template_id == sample_template.id
    
    def test_generate_is_idempotent(self, session, sample_template):
        """Calling generate twice should not create duplicates."""
        monday = date(2025, 12, 29)
        
        tasks1 = task_service.generate_tasks_for_date(session, monday)
        tasks2 = task_service.generate_tasks_for_date(session, monday)
        
        assert len(tasks1) == 1
        assert len(tasks2) == 1
        assert tasks1[0].id == tasks2[0].id
    
    def test_generate_skips_non_matching_days(self, session, sample_template):
        """Should not generate tasks for days that don't match template."""
        # Tuesday - doesn't match sample_template (weekdays="0,2,4")
        tuesday = date(2025, 12, 30)
        tasks = task_service.generate_tasks_for_date(session, tuesday)
        
        assert len(tasks) == 0


class TestTaskOperations:
    """Tests for task CRUD operations."""
    
    def test_complete_task(self, session, sample_task):
        """Test marking a task as completed."""
        task = task_service.complete_task(session, sample_task.id)
        
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
    
    def test_uncomplete_task(self, session, sample_completed_task):
        """Test marking a completed task as pending."""
        task = task_service.uncomplete_task(session, sample_completed_task.id)
        
        assert task.status == TaskStatus.PENDING
        assert task.completed_at is None
    
    def test_update_task(self, session, sample_task):
        """Test updating task properties."""
        updates = TaskUpdate(title="Updated Title", expected_minutes=25)
        task = task_service.update_task(session, sample_task.id, updates)
        
        assert task.title == "Updated Title"
        assert task.expected_minutes == 25
    
    def test_get_tasks_for_date(self, session, sample_task):
        """Test retrieving tasks for a specific date."""
        tasks = task_service.get_tasks_for_date(session, date.today())
        
        assert len(tasks) == 1
        assert tasks[0].id == sample_task.id


class TestTemplateAwareOperations:
    """Tests for template-aware task operations."""
    
    def test_reorder_task_updates_template(self, session, sample_template):
        """Reordering a template task should update the template's order."""
        # Generate a task from the template
        monday = date(2025, 12, 29)
        tasks = task_service.generate_tasks_for_date(session, monday)
        task = tasks[0]
        
        # Reorder the task
        task_service.reorder_task(session, task.id, 5)
        
        # Verify template was updated
        session.refresh(sample_template)
        assert sample_template.order == 5
    
    def test_move_weekly_task_updates_template_weekdays(self, session, sample_template):
        """Moving a weekly task should update the template's weekdays."""
        # Generate a task on Monday
        monday = date(2025, 12, 29)
        tasks = task_service.generate_tasks_for_date(session, monday)
        task = tasks[0]
        
        # Move to Tuesday (which wasn't in original weekdays)
        tuesday = date(2025, 12, 30)
        task_service.move_task_to_date(session, task.id, tuesday, 0)
        
        # Verify template weekdays were updated
        session.refresh(sample_template)
        assert "1" in sample_template.weekdays  # Tuesday added
        assert "0" not in sample_template.weekdays  # Monday removed


class TestRepeatInfo:
    """Tests for repeat_info generation."""
    
    def test_get_repeat_info_daily(self, session, sample_daily_template):
        """Daily template should return correct repeat info."""
        info = task_service.get_repeat_info(sample_daily_template)
        
        assert info is not None
        assert info.type == RepeatType.DAILY
        assert info.days == ["Mon", "Tue", "Wed", "Thu", "Fri"]
    
    def test_get_repeat_info_weekly(self, session, sample_template):
        """Weekly template should return correct repeat info."""
        info = task_service.get_repeat_info(sample_template)
        
        assert info is not None
        assert info.type == RepeatType.WEEKLY
        assert info.days == ["Mon", "Wed", "Fri"]
    
    def test_get_repeat_info_none(self, session):
        """Non-repeating template should return None."""
        template = TaskTemplate(
            title="One-off",
            priority=TaskPriority.OPTIONAL,
            repeat_type=RepeatType.NONE,
            order=0,
            expected_minutes=10,
        )
        info = task_service.get_repeat_info(template)
        
        assert info is None

