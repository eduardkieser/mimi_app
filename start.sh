#!/bin/bash
# MIMI App - Mac Development/Production Launcher
#
# Usage:
#   ./start.sh              # Start locally (localhost:8001)
#   ./start.sh --public     # Start with info to add to Cloudflare Tunnel

set -e
cd "$(dirname "$0")/backend"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}📋 MIMI Task App${NC}"
echo "================================"

# Setup Python environment if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Ensure data directory exists
mkdir -p data

# Start the server
echo ""
echo -e "${GREEN}🚀 Starting server at http://localhost:8001${NC}"
echo "   Press Ctrl+C to stop"

if [[ " $* " =~ " --public " ]]; then
    echo ""
    echo -e "${BLUE}📝 To expose publicly via Cloudflare Tunnel:${NC}"
    echo "   1. Go to Cloudflare Zero Trust → Networks → Tunnels"
    echo "   2. Edit your 'pringle-tunnel'"
    echo "   3. Add Public Hostname:"
    echo "      - Subdomain: mimi"
    echo "      - Domain: pringlelabs.com"
    echo "      - Service: http://localhost:8001"
    echo ""
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

