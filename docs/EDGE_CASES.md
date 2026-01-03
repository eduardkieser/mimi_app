# Mimi.Today Edge Cases & Behavior Specification

This document describes edge cases that arise from the "Trello-like" task management system combined with recurring task templates.

## Core Concepts

### Task Types
1. **One-time tasks**: Single tasks for a specific date, no template
2. **Daily tasks**: Generated from a template for all weekdays (Mon-Fri)
3. **Weekly tasks**: Generated from a template for specific weekdays (e.g., Mon, Wed, Fri)
4. **Monthly tasks**: Generated from a template on the same day of each month

### Task Instances vs Templates
- **Template**: Defines the rule for generating tasks (stored in `TaskTemplate`)
- **Task Instance**: A concrete task for a specific date (stored in `Task`)
- Task instances link back to their template via `template_id`

---

## Edge Cases

### 1. Moving a Weekly Task to a Day It Already Exists On

**Scenario**: A weekly task repeats on Mon, Wed, Fri. User drags the Monday instance to Friday.

**Problem**: There's already a task instance on Friday from the same template.

**Resolution**: 
- Remove the source day (Monday) from the template's weekdays
- Do NOT add to target day (already exists)
- Delete the source task instance
- Result: Template now only has Wed, Fri

**Why**: Moving to an existing day is effectively a "delete from source" operation.

---

### 2. Deleting a Daily Task Instance

**Scenario**: A daily task appears Mon-Fri. User deletes the Wednesday instance.

**Problem**: Simply deleting the task would cause it to regenerate.

**Resolution**:
- Convert the daily template to weekly
- Set weekdays to all weekdays EXCEPT the deleted day (Mon, Tue, Thu, Fri)
- Delete the task instance

**Why**: User intent is "don't show this on Wednesday anymore"

---

### 3. Deleting a Weekly Task Instance

**Scenario**: A weekly task repeats on Mon, Wed, Fri. User deletes the Wednesday instance.

**Resolution**:
- Remove Wednesday from the template's weekdays (now Mon, Fri)
- Delete the task instance
- If no weekdays remain, deactivate the template

---

### 4. Moving a Daily Task to a Different Day

**Scenario**: A daily task (Mon-Fri) exists. User drags Tuesday's instance to a different position on Thursday.

**Problem**: There's already a Thursday instance.

**Resolution**:
- If moving to same day (just reordering): Update order only
- If moving to different day that already has instance: Convert to weekly, remove source day
- If moving to weekend (Sat/Sun): Convert to weekly excluding source day, create one-time task on weekend

---

### 5. Reordering Within the Same Day

**Scenario**: User reorders tasks within a single day.

**Resolution**:
- Update `order` field on all affected task instances
- If task is template-based, also update template's `order`
- Template order affects future generated tasks

---

### 6. Editing a Recurring Task's Title/Description

**Scenario**: User edits the title of a weekly task instance.

**Current Behavior**: Only updates that specific task instance.

**Alternative Considered**: Could update the template (affects all future instances).

**Resolution**: For now, editing updates only the instance. Template editing requires using the create modal with pre-populated values.

---

### 7. Task Generation Idempotency

**Scenario**: User views a date multiple times, or page refreshes.

**Requirement**: Tasks should not duplicate.

**Resolution**: 
- `generate_tasks_for_date()` checks for existing tasks from each template
- If a task already exists for that template+date, skip generation
- Keyed by `template_id` to prevent duplicates

---

### 8. Historical Date Viewing

**Scenario**: User views a past date in Mimi client.

**Resolution**:
- Tasks are generated even for past dates (allows historical viewing)
- Past dates are read-only (cannot toggle completion)
- Shows tasks as they were (or would have been) for that date

---

### 9. Template Deactivation

**Scenario**: Last weekday is removed from a weekly template.

**Resolution**:
- Set `is_active = False` on template
- Template will not generate any new tasks
- Existing task instances remain in database for history

---

### 10. Moving Task to Weekend

**Scenario**: User drags a weekday task to Saturday or Sunday.

**Current Behavior**: 
- For daily templates: Convert to weekly, add weekend day, remove source day
- This is unusual but supported

**Future Consideration**: May want to disallow or warn, since Mimi typically only works weekdays.

---

## Summary Table

| Action | One-Time | Daily | Weekly |
|--------|----------|-------|--------|
| Delete instance | Delete task | Convert to weekly minus that day | Remove day from weekdays |
| Move to different day | Update scheduled_date | Convert to weekly, update days | Update weekdays |
| Move to existing day | N/A | Convert to weekly, remove source | Just remove source day |
| Reorder same day | Update order | Update order + template | Update order + template |
| Edit title/desc | Update task | Update task only | Update task only |

---

## Testing Requirements

All edge cases above should have corresponding integration tests that:
1. Perform the action via API
2. Verify immediate result
3. Reload tasks to verify persistence
4. Check template state where applicable

