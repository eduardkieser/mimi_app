# Mimi.Today

A task list app for household cleaning, designed to run on a local network.

## Overview

- **Mimi** (cleaner) views and completes daily tasks
- **Ilsa** (admin) manages task templates and schedules

## Running the App

### Quick Start (Development)

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Detached (Background)

To run the server so it persists after closing the terminal:

```bash
cd /Users/eduard/workspace/mimi_app/backend
source venv/bin/activate
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
echo $! > server.pid
```

This will:
- Run the server in the background
- Save logs to `server.log`
- Save the process ID to `server.pid`

### Stop the Server

```bash
kill $(cat /Users/eduard/workspace/mimi_app/backend/server.pid)
```

### Access

Once running, access from any device on your network:

| View | URL |
|------|-----|
| Mimi (tasks) | http://YOUR_IP:8000/ |
| Admin | http://YOUR_IP:8000/admin |

Find your IP with: `ipconfig getifaddr en0`

## Stack

- **Backend**: FastAPI + SQLite + SQLModel
- **Frontend**: HTMX + Alpine.js

## Development

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## License

Private / Personal Use
