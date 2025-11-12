#!/bin/bash

# Script to kill processes on ports 8000, 8001, 8002

echo "Checking for processes on ports 8000, 8001, 8002..."

# Function to kill processes on a port
kill_port() {
    local port=$1
    local pids=$(lsof -ti :$port 2>/dev/null)
    if [ -z "$pids" ]; then
        echo "✅ Port $port is free"
    else
        echo "🔪 Killing processes on port $port: $pids"
        kill -9 $pids 2>/dev/null
        echo "✅ Port $port is now free"
    fi
}

# Kill processes on each port
kill_port 8000
kill_port 8001
kill_port 8002

echo ""
echo "✅ All ports are now free!"
echo "You can now start the services."

