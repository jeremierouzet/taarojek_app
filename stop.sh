#!/bin/bash
###############################################################################
# Stop Script for Swisscom NSO Manager
# Stops the background Django development server
###############################################################################

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PID_FILE="logs/nso-manager.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  No PID file found. Is the application running?"
    echo "Checking for process on port 50478..."
    PID=$(lsof -ti:50478)
    if [ -n "$PID" ]; then
        echo "Found process $PID on port 50478"
        read -p "Kill this process? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill $PID
            echo "✓ Process stopped"
        fi
    else
        echo "No process found on port 50478"
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p $PID > /dev/null 2>&1; then
    echo "Stopping NSO Manager (PID: $PID)..."
    kill $PID
    rm -f "$PID_FILE"
    echo "✓ Application stopped"
else
    echo "⚠️  Process $PID not running"
    rm -f "$PID_FILE"
fi
