# Task Template Specification

## Overview

This document defines how task templates and task instances work in Mimi.Today.

## Core Concepts

### TaskTemplate
A template defines a recurring task pattern. Templates are the "source of truth" for recurring tasks.

**Properties:**
- `id`: Unique identifier
- `title`: Task name
- `description`: Optional details
- `priority`: `required` | `optional`
- `expected_minutes`: Time estimate
- `order`: Display position within a day
- `repeat_type`: `daily` | `weekly` | `monthly` | `none`
- `weekly_days`: List of weekdays (0=Mon, 1=Tue, ..., 4=Fri) for weekly repeat
- `active`: Whether this template is currently active

### Task (Instance)
A task instance is a concrete occurrence of a task on a specific date. Instances are created in two scenarios:

1. **Live generation**: When viewing a current/future date, tasks are generated on-the-fly from templates. These are ephemeral until the day is "closed".

2. **Historical snapshot**: At the end of each day (or when explicitly triggered), all template-generated tasks are "resolved" into permanent Task records with their completion status preserved.

**Properties:**
- `id`: Unique identifier
- `template_id`: Reference to source template (null for one-off tasks)
- `title`, `description`, `priority`, `expected_minutes`: Copied from template or set directly
- `order`: Display position
- `scheduled_date`: The specific date this task appears on
- `status`: `pending` | `completed`
- `is_snapshot`: Boolean - true if this is a historical snapshot (read-only)

## Behavior Rules

### Viewing a Day (Current/Future)

1. Query for existing Task records for that date where `is_snapshot = false`
2. Query all active templates that should appear on that date
3. For templates without a corresponding task instance, generate ephemeral tasks
4. Return merged list sorted by order

### Editing a Template-Based Task (Admin)

When editing a task that has `template_id != null`:
- **Edits update the template**, not the instance
- All future occurrences reflect the change immediately
- Past snapshots are NOT affected (history preserved)

### Moving a Task (Drag & Drop)

**Same day reorder:**
- If task has `template_id`: Update the template's `order`
- If one-off task: Update the task's `order`

**Move to different day:**
- If task has `template_id`: 
  - For weekly templates: Update the template's `weekly_days` to reflect new day(s)
  - For daily templates: This effectively removes that day? Or creates exception? (TBD - maybe disallow)
- If one-off task: Update `scheduled_date`

### Deleting a Template-Based Task

- Deleting from admin should prompt: "Delete this occurrence or all future occurrences?"
- "All" = deactivate/delete the template
- "This one" = create an exception for this date (or just hide from this date)

### End-of-Day Snapshot

A scheduled job (or triggered manually) runs at end of day:

1. For the closing date, get all template-generated tasks
2. For each, create a permanent Task record with `is_snapshot = true`
3. Copy current completion status
4. These snapshot records are immutable (read-only)

This preserves the exact state of each day for historical viewing.

### Viewing Past Days (Mimi Client)

1. Query Task records where `scheduled_date = target_date` AND `is_snapshot = true`
2. If no snapshots exist (day not yet closed), generate from templates (for same-day viewing before closure)
3. Display as read-only

## Admin UI Indicators

Tasks should visually indicate their type:

| Type | Indicator |
|------|-----------|
| One-off task | No indicator (default) |
| Daily repeating | 🔄 or "Daily" badge |
| Weekly repeating | 🔄 M/T/W/etc showing which days |
| Monthly repeating | 🔄 "Monthly" badge |

## API Changes Required

### New/Modified Endpoints

1. `PATCH /api/admin/templates/{id}` - Edit template (existing)
2. `POST /api/admin/tasks/{id}/move` - Move task (update to handle templates)
3. `POST /api/admin/close-day/{date}` - Trigger end-of-day snapshot
4. `GET /api/tasks/date/{date}` - Updated to return snapshots for past dates

### Task Response Enhancement

Add to task response:
```json
{
  "id": 1,
  "template_id": 5,
  "repeat_info": {
    "type": "weekly",
    "days": ["Mon", "Thu"]
  },
  "is_snapshot": false
}
```

## Migration Path

1. Add `is_snapshot` column to Task table (default false)
2. Add `template_id` column to Task table (nullable)
3. Update task generation logic
4. Update admin move/edit logic
5. Add snapshot job
6. Update admin UI to show repeat indicators

