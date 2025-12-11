# Mimi.Today

A gamified task list app for household cleaning, designed to run on a local network.

## Overview

- **Mimi** (cleaner) accesses `mimi.today` to view and complete daily tasks
- **Ilsa** (admin) accesses `ilsa.admin` to manage task templates and schedules

## Features

- Color-coded task cards: 🔴 Required → 🟢 Done, 🟡 Optional → 🟢 Done
- Satisfying sound feedback on task completion
- Weekly recurring tasks with easy overrides
- Task completion history

## Stack

- **Backend**: FastAPI + SQLite
- **Frontend Option 1**: Flutter Web (PWA)
- **Frontend Option 2**: HTMX + Alpine.js (ultra-lightweight)
- **Deployment**: Docker Compose + Caddy reverse proxy

## Quick Start

```bash
docker-compose up -d
```

Then configure local DNS to point `mimi.today` and `ilsa.admin` to your server.

See `docs/` for detailed setup guides.

## Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Flutter
cd frontend_flutter
flutter pub get
flutter run -d chrome
```

## License

Private / Personal Use

