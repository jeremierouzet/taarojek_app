#!/bin/bash
###############################################################################
# Setup Script for Swisscom NSO Manager
# This script sets up the application after git clone
# Cross-platform: macOS, Linux, Windows (Git Bash/WSL)
###############################################################################

set -e  # Exit on error

echo "=========================================="
echo "Swisscom NSO Manager - Setup Script"
echo "=========================================="
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS
OS_TYPE=$(uname -s)
case "$OS_TYPE" in
    Linux*)     OS_NAME="Linux";;
    Darwin*)    OS_NAME="macOS";;
    MINGW*|MSYS*|CYGWIN*)     OS_NAME="Windows";;
    *)          OS_NAME="Unknown";;
esac

echo -e "${BLUE}Detected OS: ${OS_NAME}${NC}"
echo ""

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if Python 3.9+ is available
echo -e "${BLUE}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 is not installed. Please install Python 3.9 or higher.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Create virtual environment
echo -e "${BLUE}Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓ pip upgraded${NC}"

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run migrations
echo -e "${BLUE}Running database migrations...${NC}"
python manage.py migrate
echo -e "${GREEN}✓ Database migrations complete${NC}"

# Create superuser
echo -e "${BLUE}Creating default user...${NC}"
python manage.py shell << EOF
from django.contrib.auth.models import User
username = 'taarojek'
password = 'Sheyratan.0150n!'
if not User.objects.filter(username=username).exists():
    User.objects.create_user(username=username, password=password, is_staff=True, is_superuser=True)
    print('✓ User created: taarojek')
else:
    print('✓ User already exists: taarojek')
EOF

echo ""
echo -e "${GREEN}=========================================="
echo "Setup Complete!"
echo "==========================================${NC}"
echo ""
echo "To start the application:"
if [ "$OS_NAME" = "Windows" ]; then
    echo "  1. Activate virtual environment: source venv/Scripts/activate"
else
    echo "  1. Activate virtual environment: source venv/bin/activate"
fi
echo "  2. Start server: python manage.py runserver 50478"
echo ""
echo "Or use the run script:"
if [ "$OS_NAME" = "Windows" ]; then
    echo "  bash run.sh (in Git Bash) or ./run.sh (in WSL)"
else
    echo "  ./run.sh"
fi
echo ""
echo "Access at: http://localhost:50478"
echo ""
if [ "$OS_NAME" = "Windows" ]; then
    echo -e "${YELLOW}Note: On Windows, ensure OpenSSH client is installed for SSH tunnels.${NC}"
    echo -e "${YELLOW}You can install it via: Settings > Apps > Optional Features > OpenSSH Client${NC}"
    echo ""
fi
