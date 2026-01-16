#!/bin/bash
###############################################################################
# Run Script for Swisscom NSO Manager
# Starts the Django development server on port 50478
###############################################################################

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
fi

# Activate virtual environment
source venv/bin/activate

# Source user's zshrc to get NSO credentials if running in zsh environment
if [ -f "$HOME/.zshrc" ]; then
    # Export only the NSO credential variables
    export $(grep -E '^export NSO_(USER|PASS)' "$HOME/.zshrc" | sed 's/^export //' | xargs)
fi

# Check for required environment variables
if [ -z "$NSO_USER_INT" ] || [ -z "$NSO_PASS_INT" ]; then
    echo "⚠️  Warning: NSO credentials not found in environment"
    echo "Please ensure these variables are set in ~/.zshrc:"
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

# Start the server in background
nohup python manage.py runserver 50478 > logs/nso-manager.log 2>&1 &
PID=$!

# Save PID to file
echo $PID > logs/nso-manager.pid

echo "✓ Application started in background (PID: $PID)"
echo "Logs: tail -f logs/nso-manager.log"
echo "Stop: kill \$(cat logs/nso-manager.pid)"
echo ""
