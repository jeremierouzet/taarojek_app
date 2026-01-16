#!/bin/bash
###############################################################################
# Stop Script for Swisscom NSO Manager
# Stops the background Django development server
# Cross-platform: macOS, Linux, Windows (Git Bash/WSL)
###############################################################################

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Detect OS
OS_TYPE=$(uname -s)
case "$OS_TYPE" in
    Linux*)     OS_NAME="Linux";;
    Darwin*)    OS_NAME="macOS";;
    MINGW*|MSYS*|CYGWIN*)     OS_NAME="Windows";;
    *)          OS_NAME="Unknown";;
esac

PID_FILE="logs/nso-manager.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  No PID file found. Is the application running?"
    echo "Checking for process on port 50478..."
    
    # Platform-specific port checking
    if [ "$OS_NAME" = "Windows" ]; then
        # Windows: use netstat
        PID=$(netstat -ano | grep ":50478" | grep "LISTENING" | awk '{print $5}' | head -n 1)
    else
        # Unix-like: check if lsof is available
        if command -v lsof &> /dev/null; then
            PID=$(lsof -ti:50478)
        else
            # Fallback to netstat if lsof not available
            PID=$(netstat -tulpn 2>/dev/null | grep ":50478" | awk '{print $7}' | cut -d'/' -f1)
        fi
    fi
    
    if [ -n "$PID" ]; then
        echo "Found process $PID on port 50478"
        read -p "Kill this process? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ "$OS_NAME" = "Windows" ]; then
                taskkill //PID $PID //F
            else
                kill $PID
            fi
            echo "✓ Process stopped"
        fi
    else
        echo "No process found on port 50478"
    fi
    exit 0
fi

PID=$(cat "$PID_FILE")

# Check if process is running (cross-platform)
process_running=false
if [ "$OS_NAME" = "Windows" ]; then
    # Windows: use tasklist
    if tasklist //FI "PID eq $PID" 2>NUL | grep -q "$PID"; then
        process_running=true
    fi
else
    # Unix-like: use ps
    if ps -p $PID > /dev/null 2>&1; then
        process_running=true
    fi
fi

if [ "$process_running" = true ]; then
    echo "Stopping NSO Manager (PID: $PID)..."
    
    if [ "$OS_NAME" = "Windows" ]; then
        taskkill //PID $PID //F
    else
        kill $PID
    fi
    
    rm -f "$PID_FILE"
    echo "✓ Application stopped"
else
    echo "⚠️  Process $PID not running"
    rm -f "$PID_FILE"
fi
