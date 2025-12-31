#!/bin/bash
# Stop MIMI App
echo "Stopping MIMI..."
pkill -f "uvicorn.*8001" 2>/dev/null || true
echo "✓ Stopped"

