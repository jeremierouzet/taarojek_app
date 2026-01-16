#!/bin/bash
###############################################################################
# Install NSO Manager as a systemd service
###############################################################################

set -e

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=========================================="
echo "NSO Manager - Service Installation"
echo "==========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Get current user (the one who ran sudo)
ACTUAL_USER=${SUDO_USER:-$USER}

# Load NSO credentials from user's zshrc if available
ZSHRC_FILE="/home/$ACTUAL_USER/.zshrc"
if [ -f "$ZSHRC_FILE" ]; then
    echo -e "${BLUE}Loading NSO credentials from ~/.zshrc...${NC}"
    
    # Extract credentials from zshrc
    NSO_USER_INT=$(grep "^export NSO_USER_INT=" "$ZSHRC_FILE" | sed "s/export NSO_USER_INT=//;s/'//g;s/\"//g")
    NSO_PASS_INT=$(grep "^export NSO_PASS_INT=" "$ZSHRC_FILE" | sed "s/export NSO_PASS_INT=//;s/'//g;s/\"//g")
    NSO_USER_E2E=$(grep "^export NSO_USER_E2E=" "$ZSHRC_FILE" | sed "s/export NSO_USER_E2E=//;s/'//g;s/\"//g")
    NSO_PASS_E2E=$(grep "^export NSO_PASS_E2E=" "$ZSHRC_FILE" | sed "s/export NSO_PASS_E2E=//;s/'//g;s/\"//g")
    NSO_USER_PROD=$(grep "^export NSO_USER_PROD=" "$ZSHRC_FILE" | sed "s/export NSO_USER_PROD=//;s/'//g;s/\"//g")
    NSO_PASS_PROD=$(grep "^export NSO_PASS_PROD=" "$ZSHRC_FILE" | sed "s/export NSO_PASS_PROD=//;s/'//g;s/\"//g")
    
    if [ -n "$NSO_USER_INT" ] && [ -n "$NSO_PASS_INT" ]; then
        echo -e "${GREEN}✓ NSO credentials loaded from ~/.zshrc${NC}"
    else
        echo -e "${YELLOW}⚠ Could not find NSO credentials in ~/.zshrc${NC}"
        echo "Please enter credentials manually:"
    fi
fi

# Prompt for missing credentials
if [ -z "$NSO_USER_INT" ] || [ -z "$NSO_PASS_INT" ]; then
    echo -e "${YELLOW}NSO Integration credentials:${NC}"
    read -p "NSO Username (NSO_USER_INT): " NSO_USER_INT
    read -sp "NSO Password (NSO_PASS_INT): " NSO_PASS_INT
    echo ""
fi

if [ -z "$NSO_USER_E2E" ] || [ -z "$NSO_PASS_E2E" ]; then
    echo -e "${YELLOW}NSO E2E credentials:${NC}"
    read -p "NSO Username (NSO_USER_E2E) [same as INT]: " NSO_USER_E2E
    NSO_USER_E2E=${NSO_USER_E2E:-$NSO_USER_INT}
    read -sp "NSO Password (NSO_PASS_E2E) [same as INT]: " NSO_PASS_E2E
    NSO_PASS_E2E=${NSO_PASS_E2E:-$NSO_PASS_INT}
    echo ""
fi

if [ -z "$NSO_USER_PROD" ] || [ -z "$NSO_PASS_PROD" ]; then
    echo -e "${YELLOW}NSO Production credentials:${NC}"
    read -p "NSO Username (NSO_USER_PROD) [same as INT]: " NSO_USER_PROD
    NSO_USER_PROD=${NSO_USER_PROD:-$NSO_USER_INT}
    read -sp "NSO Password (NSO_PASS_PROD) [same as INT]: " NSO_PASS_PROD
    NSO_PASS_PROD=${NSO_PASS_PROD:-$NSO_PASS_INT}
    echo ""
fi

echo ""

# Create service file from template
SERVICE_FILE="/etc/systemd/system/nso-manager.service"
echo -e "${BLUE}Creating service file at $SERVICE_FILE...${NC}"

sed -e "s|%USERNAME%|$ACTUAL_USER|g" \
    -e "s|%INSTALL_DIR%|$SCRIPT_DIR|g" \
    -e "s|%NSO_USER_INT%|$NSO_USER_INT|g" \
    -e "s|%NSO_PASS_INT%|$NSO_PASS_INT|g" \
    -e "s|%NSO_USER_E2E%|$NSO_USER_E2E|g" \
    -e "s|%NSO_PASS_E2E%|$NSO_PASS_E2E|g" \
    -e "s|%NSO_USER_PROD%|$NSO_USER_PROD|g" \
    -e "s|%NSO_PASS_PROD%|$NSO_PASS_PROD|g" \
    "$SCRIPT_DIR/nso-manager.service.template" > "$SERVICE_FILE"

echo -e "${GREEN}✓ Service file created${NC}"

# Reload systemd
echo -e "${BLUE}Reloading systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ systemd reloaded${NC}"

# Enable service
echo -e "${BLUE}Enabling service...${NC}"
systemctl enable nso-manager.service
echo -e "${GREEN}✓ Service enabled${NC}"

# Start service
echo -e "${BLUE}Starting service...${NC}"
systemctl start nso-manager.service
echo -e "${GREEN}✓ Service started${NC}"

echo ""
echo -e "${GREEN}=========================================="
echo "Installation Complete!"
echo "==========================================${NC}"
echo ""
echo "Service commands:"
echo "  Status:  sudo systemctl status nso-manager"
echo "  Start:   sudo systemctl start nso-manager"
echo "  Stop:    sudo systemctl stop nso-manager"
echo "  Restart: sudo systemctl restart nso-manager"
echo "  Logs:    sudo journalctl -u nso-manager -f"
echo ""
echo "Access at: http://localhost:50478"
echo ""
