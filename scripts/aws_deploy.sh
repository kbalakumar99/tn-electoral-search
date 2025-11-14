#!/bin/bash
# AWS Deployment Script - Pull latest code and restart server
# Usage: ./scripts/aws_deploy.sh

set -e  # Exit on error

echo "🚀 Starting AWS deployment..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${YELLOW}📂 Current directory: $(pwd)${NC}"

# Pull latest changes from GitHub
echo -e "\n${YELLOW}📥 Pulling latest changes from GitHub...${NC}"
git fetch origin
git pull origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Code updated successfully${NC}"
else
    echo -e "${RED}✗ Failed to pull from GitHub${NC}"
    exit 1
fi

# Install/update dependencies if requirements changed
if git diff HEAD@{1} HEAD --name-only | grep -q "requirements"; then
    echo -e "\n${YELLOW}📦 Requirements changed, updating dependencies...${NC}"
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip install -r requirements.txt --quiet
        echo -e "${GREEN}✓ Dependencies updated${NC}"
    else
        echo -e "${YELLOW}⚠ Virtual environment not found, skipping dependency update${NC}"
    fi
fi

# Find and stop the running server
echo -e "\n${YELLOW}🛑 Stopping current server...${NC}"

# Try multiple methods to stop the server
SERVER_STOPPED=false

# Method 1: systemd service
if systemctl is-active --quiet tn-electoral-search 2>/dev/null; then
    echo "  - Stopping systemd service..."
    sudo systemctl stop tn-electoral-search
    SERVER_STOPPED=true
fi

# Method 2: pkill uvicorn/fastapi
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    echo "  - Killing uvicorn processes..."
    pkill -f "uvicorn.*main:app" || true
    sleep 2
    SERVER_STOPPED=true
fi

# Method 3: Kill Python processes running main.py
if pgrep -f "python.*main.py" > /dev/null; then
    echo "  - Killing Python main.py processes..."
    pkill -f "python.*main.py" || true
    sleep 2
    SERVER_STOPPED=true
fi

if [ "$SERVER_STOPPED" = true ]; then
    echo -e "${GREEN}✓ Server stopped${NC}"
else
    echo -e "${YELLOW}⚠ No running server found${NC}"
fi

# Start the server
echo -e "\n${YELLOW}🚀 Starting server...${NC}"

# Method 1: Try systemd service first
if systemctl list-unit-files | grep -q "tn-electoral-search.service"; then
    echo "  - Starting via systemd..."
    sudo systemctl start tn-electoral-search
    sleep 3
    
    if systemctl is-active --quiet tn-electoral-search; then
        echo -e "${GREEN}✓ Server started successfully via systemd${NC}"
        echo -e "\n${GREEN}📊 Service status:${NC}"
        sudo systemctl status tn-electoral-search --no-pager -l
    else
        echo -e "${RED}✗ Failed to start via systemd${NC}"
        exit 1
    fi
    
# Method 2: Manual start with uvicorn in background
else
    echo "  - Starting manually with uvicorn..."
    
    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        echo -e "${RED}✗ Virtual environment not found at: venv${NC}"
        echo -e "${YELLOW}Please create it with: python3 -m venv venv${NC}"
        exit 1
    fi
    
    source venv/bin/activate
    
    # Start server in background
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1 &
    SERVER_PID=$!
    
    echo -e "${GREEN}✓ Server started with PID: $SERVER_PID${NC}"
    echo "  - Logs: $PROJECT_ROOT/server.log"
    
    # Wait a bit and check if server is running
    sleep 3
    if ps -p $SERVER_PID > /dev/null; then
        echo -e "${GREEN}✓ Server is running${NC}"
    else
        echo -e "${RED}✗ Server failed to start. Check logs:${NC}"
        tail -20 server.log
        exit 1
    fi
fi

# Health check
echo -e "\n${YELLOW}🏥 Performing health check...${NC}"
sleep 2

# Try to hit the health endpoint
if curl -s -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${YELLOW}⚠ Health check failed (server might still be starting)${NC}"
fi

echo -e "\n${GREEN}✅ Deployment complete!${NC}"
echo -e "\n${YELLOW}Access your application at:${NC}"
echo -e "  - http://localhost:8000"
echo -e "  - http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo 'YOUR-EC2-IP'):8000"

echo -e "\n${YELLOW}Useful commands:${NC}"
echo -e "  - View logs: tail -f $PROJECT_ROOT/server.log"
echo -e "  - Check status: systemctl status tn-electoral-search"
echo -e "  - Stop server: pkill -f 'uvicorn.*main:app'"
