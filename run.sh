#!/bin/bash
###############################################################################
# Run Script for Swisscom NSO Manager
# Starts the Django development server on port 50478
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

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
fi

# Activate virtual environment (platform-specific)
if [ "$OS_NAME" = "Windows" ]; then
    # Windows uses Scripts instead of bin
    if [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
    else
        echo "Error: Could not find venv/Scripts/activate"
        exit 1
    fi
else
    # Unix-like systems (macOS, Linux)
    source venv/bin/activate
fi

# Source user's shell config to get NSO credentials
# Try multiple config files
for config_file in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
    if [ -f "$config_file" ]; then
        # Export only the NSO credential variables
        if grep -q "NSO_USER" "$config_file" 2>/dev/null; then
            export $(grep -E '^export NSO_(USER|PASS)' "$config_file" 2>/dev/null | sed 's/^export //' | xargs)
            break
        fi
    fi
done

# Check for required environment variables
if [ -z "$NSO_USER_INT" ] || [ -z "$NSO_PASS_INT" ]; then
    echo "⚠️  Warning: NSO credentials not found in environment"
    echo "Please ensure these variables are set in your shell config:"
    echo "  - NSO_USER_INT / NSO_PASS_INT (for integration)"
    echo "  - NSO_USER_E2E / NSO_PASS_E2E (for E2E)"
    echo "  - NSO_USER_PROD / NSO_PASS_PROD (for production)"
    echo ""
else
    echo "✓ NSO credentials loaded from environment"
fi

echo "Starting Swisscom NSO Manager on port 50478..."
echo "Access at: http://localhost:50478"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Platform-specific background execution
if [ "$OS_NAME" = "Windows" ]; then
    # Windows: use start command or run in background
    echo "Note: Running on Windows - starting in background mode"
    python manage.py runserver 50478 > logs/nso-manager.log 2>&1 &
    PID=$!
else
    # Unix-like: use nohup
    nohup python manage.py runserver 50478 > logs/nso-manager.log 2>&1 &
    PID=$!
fi

# Save PID to file
echo $PID > logs/nso-manager.pid

echo "✓ Application started in background (PID: $PID)"
echo "Logs: tail -f logs/nso-manager.log"
if [ "$OS_NAME" = "Windows" ]; then
    echo "Stop: ./stop.sh or taskkill /PID $PID /F"
else
    echo "Stop: ./stop.sh or kill \$(cat logs/nso-manager.pid)"
fi
echo ""
