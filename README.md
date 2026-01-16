# Swisscom NSO Manager

Django web application for managing NSO instances and checking device synchronization status.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [NSO Instance Configuration](#nso-instance-configuration)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Deployment Checklist](#deployment-checklist)
- [Troubleshooting](#troubleshooting)

## Features

- **Multi-Instance Support**: Connect to 5 different NSO environments (Dune and Titan: Integration, E2E, Production)
- **Simultaneous Connections**: Connect to multiple NSO instances at the same time with unique local ports
- **SSH Tunnel Management**: Automatically creates SSH tunnels to NSO instances through jump host
- **Device Sync Checking**: Check if all devices are synchronized with NSO
- **Swisscom Branding**: Custom UI with Swisscom corporate design
- **Authentication**: Secure login system with username/password
- **Service Mode**: Can run as a systemd service for production deployment

## Quick Start

### After Git Clone

```bash
# 1. Clone the repository
git clone https://github.com/jeremierouzet/taarojek_app.git
cd taarojek_app

# 2. Run setup (one-time)
./setup.sh

# 3. Start the application
./run.sh

# 4. View logs (optional)
tail -f logs/nso-manager.log

# 5. Stop the application
./stop.sh
```

**Access:** http://localhost:50478

**Default Login:**
- Username: `taarojek`
- Password: `Sheyratan.0150n!`

## NSO Instance Configuration

### Available Instances

| Instance | Environment | Platform | Remote IP | Remote Port | Local Port | Access URL |
|----------|------------|----------|-----------|-------------|------------|------------|
| **Dune Integration** | Integration | Dune | 138.188.202.5 | 8888 | **8888** | https://localhost:8888 |
| **Titan Integration** | Integration | Titan | 138.188.200.227 | 8888 | **8889** | https://localhost:8889 |
| **Dune E2E** | End-to-End | Dune | 138.188.202.6 | 8888 | **8890** | https://localhost:8890 |
| **Titan E2E** | End-to-End | Titan | 138.188.200.192 | 8888 | **8891** | https://localhost:8891 |
| **Titan Production** | Production | Titan | 138.188.195.223 | 8888 | **8892** | https://localhost:8892 |

### Multi-Instance Support

- **Connect to all 5 instances simultaneously** - each gets its own SSH tunnel
- **Unique local ports** (8888-8892) prevent conflicts
- **Direct NSO UI access** via localhost URLs when connected
- **Parallel operations** across multiple environments

## Installation

### Prerequisites

- Python 3.9+
- SSH access to devm (with ProxyJump configuration in `~/.ssh/config`)
- NSO credentials in environment variables (optional for development):
  - `NSO_USER_INT`
  - `NSO_PASS_INT`

### Method 1: Quick Setup (Recommended)

After cloning the repository, simply run:

```bash
./setup.sh
./run.sh
```

### Method 2: Manual Installation

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create admin user:**
   ```bash
   python manage.py createsuperuser
   ```

5. **Start server:**
   ```bash
   python manage.py runserver 50478
   ```

### Method 3: Install as System Service

For production deployment:

```bash
./setup.sh                    # First run setup
sudo ./install-service.sh     # Install and start service
```

**Service Features:**
- Starts automatically on system boot
- Restarts automatically if it crashes
- Runs on port 50478

**Service Commands:**
```bash
sudo systemctl status nso-manager   # Check status
sudo systemctl start nso-manager    # Start
sudo systemctl stop nso-manager     # Stop
sudo systemctl restart nso-manager  # Restart
sudo journalctl -u nso-manager -f   # View logs
```

## Usage

### Starting the Application

**Development Mode (Background):**
```bash
./run.sh                      # Starts in background
tail -f logs/nso-manager.log  # View logs
./stop.sh                     # Stop application
```

**Development Mode (Foreground):**
```bash
source venv/bin/activate
python manage.py runserver 50478
```

**Service Mode:**
```bash
sudo systemctl start nso-manager
```

### Using the Application

1. **Login:** Navigate to http://localhost:50478
   - Username: `taarojek` / Password: `Sheyratan.0150n!`

2. **Connect to NSO Instance(s):**
   - Click "Connect" on one or more instance cards
   - SSH tunnels are created automatically through devm
   - You can connect to all 5 instances simultaneously

3. **Access NSO UI Directly:**
   - Once connected, use the local port URLs (see table above)
   - Example: https://localhost:8888 for Dune Integration

4. **Check Device Sync:**
   - Click "Check Devices" on any connected instance
   - View sync statistics and detailed device status
   - Refresh as needed

5. **Disconnect:**
   - Click "Disconnect" to close SSH tunnels
   - Or keep them running for quick access

### Checking Active Tunnels

View all active tunnels:
```bash
ps aux | grep "ssh -L"
```

Check specific ports:
```bash
lsof -i :8888  # Dune Integration
lsof -i :8889  # Titan Integration
lsof -i :8890  # Dune E2E
lsof -i :8891  # Titan E2E
lsof -i :8892  # Titan Production
```

## Project Structure

```
taarojek_app/
├── nso_manager/              # Django project settings
│   ├── settings.py           # Django configuration
│   ├── urls.py               # URL routing
│   └── nso_config.py         # NSO instance configurations
├── device_sync/              # Main application
│   ├── views.py              # View logic and authentication
│   ├── urls.py               # URL routing
│   ├── ssh_tunnel.py         # SSH tunnel management
│   ├── nso_client.py         # NSO REST API client
│   └── templates/            # HTML templates with Swisscom branding
├── setup.sh                  # Automated setup script
├── run.sh                    # Quick start script
├── install-service.sh        # Systemd service installer
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

### Key Components

**SSH Tunnel Manager** (`device_sync/ssh_tunnel.py`)
- Creates SSH tunnels: `ssh -L LOCAL_PORT:NSO_IP:8888 -N -f devm`
- Each instance uses unique local port (8888-8892)
- Supports multiple simultaneous connections
- Manages tunnel lifecycle (create, check, close)

**NSO Client** (`device_sync/nso_client.py`)
- REST API integration with NSO
- Device listing and sync checking
- Authentication handling
- SSL verification disabled (for internal use)

## Deployment Checklist

### First Time Setup

- [ ] Clone repository
- [ ] Run `./setup.sh`
- [ ] Configure NSO instance IPs if needed
- [ ] Set NSO credentials in environment
- [ ] Verify SSH access to devm

### Production Deployment

- [ ] Run setup script
- [ ] Update NSO credentials
- [ ] Install as service: `sudo ./install-service.sh`
- [ ] Verify service status
- [ ] Test connections to all instances
- [ ] Change default password

### Git Repository Setup

```bash
cd taarojek_app
git init
git add .
git commit -m "Initial commit: NSO Manager application"
git remote add origin https://github.com/jeremierouzet/taarojek_app.git
git branch -M main
git push -u origin main
```

## Configuration

### NSO Credentials

The application requires NSO credentials to be set in environment variables. Add these to your `~/.zshrc` file:

```bash
# NSO Integration Environment
export NSO_USER_INT='adm1-taarojek'
export NSO_PASS_INT='your_password_here'

# NSO E2E Environment
export NSO_USER_E2E='adm1-taarojek'
export NSO_PASS_E2E='your_password_here'

# NSO Production Environment
export NSO_USER_PROD='adm1-taarojek'
export NSO_PASS_PROD='your_password_here'
```

After editing `~/.zshrc`, reload it:
```bash
source ~/.zshrc
```

The `run.sh` script automatically loads these credentials from your `.zshrc` file.

### Updating NSO Instances

Edit [nso_manager/nso_config.py](nso_manager/nso_config.py) to modify NSO instance configurations:

```python
NSO_INSTANCES = {
    'dune-integration': {
        'name': 'Dune Integration',
        'ip': '138.188.202.5',
        'port': 8888,
        'local_port': 8888,  # Unique local port
        'ssh_host': 'devm',
        'username': os.getenv('NSO_USER_INT', 'admin'),  # From environment
        'password': os.getenv('NSO_PASS_INT', 'admin'),
        # ... other config
    },
    # ... other instances
}
```

**Note:** Credentials are automatically read from environment variables based on the instance's environment (integration/e2e/production).

**Note:** Credentials are automatically read from environment variables based on the instance's environment (integration/e2e/production).

### Changing Default User

```bash
source venv/bin/activate
python manage.py changepassword taarojek
```

Or create a new admin user:
```bash
python manage.py createsuperuser
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :50478
kill <PID>

# Or find NSO tunnel ports
sudo lsof -i :8888
```

### SSH Tunnel Issues

**Problem: Connection refused**
```bash
# Test SSH access
ssh devm "echo Connection OK"

# Verify NSO instance is running
ssh devm "curl -k https://138.188.202.5:8888"
```

**Problem: Tunnel not created**
```bash
# Check active tunnels
ps aux | grep "ssh -L"

# Manual tunnel test
ssh -L 8888:138.188.202.5:8888 -N devm
# Try: curl -k https://localhost:8888
```

**Problem: Multiple tunnels conflict**
- Each NSO instance uses a unique local port (8888-8892)
- Check tunnel status in application UI
- Close unused tunnels before creating new ones

### Authentication Issues

**Problem: Can't login**
```bash
# Verify user exists
./manage.py shell -c "from django.contrib.auth.models import User; print(User.objects.filter(username='taarojek').exists())"

# Reset password
./manage.py changepassword taarojek
```

### NSO Connection Issues

**Problem: NSO returns 401 Unauthorized**
- Update NSO credentials in `nso_config.py` or set environment variables:
```bash
export NSO_USERNAME="your_username"
export NSO_PASSWORD="your_password"
```

**Problem: Device sync check fails**
- Verify tunnel is active (check application homepage)
- Test REST API manually:
```bash
curl -k -u admin:admin https://localhost:8888/restconf/data/tailf-ncs:devices/device
```

### Service Issues

**Problem: Service won't start**
```bash
# Check service status
sudo systemctl status nso-manager

# View logs
sudo journalctl -u nso-manager -f

# Check for errors
sudo systemctl restart nso-manager
```

**Problem: Service starts but can't access**
- Verify port in service file matches 50478
- Check firewall: `sudo ufw status`
- Test locally: `curl http://localhost:50478`

### Database Issues

**Problem: Migration errors**
```bash
# Reset database
rm -f db.sqlite3
./manage.py migrate
./manage.py createsuperuser --username taarojek --email taarojek@example.com
```

### General Debugging

**Enable Django Debug Mode**

Edit [nso_manager/settings.py](nso_manager/settings.py):
```python
DEBUG = True
```
Restart the application to see detailed error messages.

**Check Application Logs**

Development mode:
```bash
./run.sh  # Logs appear in terminal
```

Service mode:
```bash
sudo journalctl -u nso-manager -f --no-pager
```

### Network Configuration

**SSH Config Verification**

Ensure ~/.ssh/config has:
```
Host devm
    HostName 138.188.200.206
    User taarojek
    ProxyJump taarojek@jump01
```

Test:
```bash
ssh devm "hostname && whoami"
```

## Development

To extend functionality:

1. **Add new NSO instances:** Edit [nso_manager/nso_config.py](nso_manager/nso_config.py)
2. **Add new views:** Update [device_sync/views.py](device_sync/views.py)
3. **Modify templates:** Edit files in `device_sync/templates/`
4. **Update styles:** Modify CSS in `base.html`

## Security Notes

- Default credentials: `taarojek` / `Sheyratan.0150n!` - **Change in production**
- SSL verification disabled for NSO connections (internal use only)
- Tunnels use SSH key authentication
- Application runs on port 50478
- Service runs as current user, not root

## License

Copyright © 2026 Swisscom AG. All rights reserved.

## Support

For issues or questions, contact: taarojek@swisscom.com
