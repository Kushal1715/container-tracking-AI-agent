#!/bin/bash

# Script to start all services for PNCT Container Query System
# This script starts all services in separate terminal windows/tabs

echo "============================================================"
echo "PNCT Container Query System - Starting All Services"
echo "============================================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Creating .env.example for reference"
    echo "   Please create .env file with your configuration"
    echo ""
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "✅ Virtual environment found"
    source venv/bin/activate
else
    echo "⚠️  Warning: Virtual environment not found"
    echo "   Create one with: python3 -m venv venv"
    echo ""
fi

# Function to start a service in a new terminal
start_service() {
    local service_name=$1
    local command=$2
    local port=$3
    
    echo "Starting $service_name on port $port..."
    
    # Try different terminal emulators
    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --tab --title="$service_name" -- bash -c "$command; exec bash"
    elif command -v xterm &> /dev/null; then
        xterm -T "$service_name" -e "$command" &
    elif command -v osascript &> /dev/null; then
        # macOS
        osascript -e "tell application \"Terminal\" to do script \"cd $(pwd) && $command\""
    else
        echo "⚠️  Could not open new terminal. Run manually:"
        echo "   $command"
        echo ""
        return 1
    fi
    
    sleep 2  # Give service time to start
    return 0
}

echo "Starting services..."
echo ""

# 1. FastAPI Backend (Port 8000)
start_service "FastAPI Backend" "source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000" "8000"

# 2. MCP Tool Server (Port 8001)
start_service "MCP Tool Server" "source venv/bin/activate && python -m mcp_tools.http_server" "8001"

# 3. Scraper API (Port 8002)
start_service "Scraper API" "source venv/bin/activate && python scraper_api.py" "8002"

# 4. Streamlit Chat Interface (Port 8501)
start_service "Streamlit Chat" "source venv/bin/activate && streamlit run streamlit_app.py" "8501"

echo ""
echo "============================================================"
echo "Services Started"
echo "============================================================"
echo ""
echo "Services are running in separate terminal windows/tabs:"
echo "  ✅ FastAPI Backend:    http://localhost:8000"
echo "  ✅ MCP Tool Server:    http://localhost:8001"
echo "  ✅ Scraper API:        http://localhost:8002"
echo "  ✅ Streamlit Chat:     http://localhost:8501"
echo ""
echo "Next steps:"
echo "  1. Start Temporal server: temporal server start-dev"
echo "  2. Start Temporal worker: python worker.py"
echo "  3. Open chat interface: http://localhost:8501"
echo "  4. Test the system: python test_integration.py"
echo ""
echo "To stop all services, close the terminal windows or press Ctrl+C"
echo ""

