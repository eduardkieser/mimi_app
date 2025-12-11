# Design Decisions

Living document - prune as decisions solidify or become obsolete.

## Mimi Client (Cleaner View)

### Keep
- Date at top (simple, unobtrusive)
- Task cards with height weighted by expected time
- Color coding: red=required, yellow=optional, green=completed
- Theme toggle (dark/solid)
- Pull-to-refresh on scroll boundaries

### Removed
- Progress bar - unnecessary visual clutter
- "All done" celebration - too gamified
- Title/subtitle headers - keep it minimal
- Emojis in UI - keep it professional

### Style
- Minimalist, functional
- Two themes: dark (border accents) and solid (filled cards)
- Cards stay in admin-set order, don't reorder on completion

---

## Admin Panel (Ilsa View)

### Keep
- 7-day horizontal scroll (today + 6 days)
- Day selector dots at top
- Insert "+" buttons between tasks (always visible)
- Drag-and-drop for reordering and moving between days
- Total time per day (subtle, in header)
- Task form: title, priority dropdown (colored), time stepper, repeat checkbox, description (optional)

### UX
- Mouse wheel scrolls horizontally through days
- Panels left-aligned (no empty space)
- Small "+" buttons to insert at specific positions

---

## Data Model

- **TaskTemplate**: Recurring task definition (weekly default)
- **Task**: Daily instance, generated from template or created ad-hoc
- `expected_minutes`: Time estimate (10-min increments)
- `priority`: optional (default) or required
- `order`: Display order set by admin

---

## Tech Stack

- Backend: FastAPI + SQLite + SQLModel
- Frontend: HTMX + Alpine.js (lightweight, server-driven)
- Deployment: Docker Compose + Caddy (planned)

---

## Open Questions

- [ ] Flutter version - still planned?
- [ ] Local DNS setup (mimi.today, ilsa.admin)
- [ ] Recurring task generation - automatic or manual trigger?

