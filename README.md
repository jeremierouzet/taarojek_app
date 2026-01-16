# Swisscom NSO Manager

Django web application for managing NSO instances and checking device synchronization status.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
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
- **SSH Tunnel Management**: Automatically creates SSH tunnels to NSO instances through jump host (disabled on dev-vm)
  - **Smart Tunnel Detection**: Automatically detects and kills existing tunnels before reconnecting
  - **Cross-Platform**: Works on Windows, macOS, and Linux
- **Direct Access Mode**: Detects when running on dev-vm and connects directly to NSO without tunnels
- **Device Sync Checking**: Check if all devices are synchronized with NSO using RESTCONF API
- **Robust NSO Client**: Curl-based client handles NSO connection behavior and SSL/TLS issues
- **Swisscom Branding**: Custom UI with Swisscom corporate design
- **Authentication**: Secure login system with username/password
- **Service Mode**: Can run as a systemd service for production deployment (Linux)
- **Background Execution**: Runs with nohup for persistent operation
- **Cross-Platform Scripts**: Shell scripts work on macOS, Linux, and Windows (Git Bash/WSL)

## Prerequisites

### System Requirements

- **Python**: 3.9 or higher
- **Operating System**: macOS, Linux, or Windows (Git Bash/WSL)
- **SSH Client**: OpenSSH for tunnel management
- **curl**: Command-line tool for HTTP requests (used for NSO API calls)
  - macOS/Linux: Pre-installed
  - Windows: Install via Git Bash or use WSL

### Required Ports

The following ports must be available on your local machine:

- **50478**: Django web application server
- **8888-8892**: SSH tunnel local endpoints (one per NSO instance)

### Required Environment Variables

**CRITICAL**: Environment variables must be defined in your shell configuration file, not just exported in the current terminal session.

Add these to `~/.zshrc`, `~/.bashrc`, or `~/.bash_profile`:

```bash
# Integration environments (Dune & Titan Integration)
export NSO_USER_INT="your_username"
export NSO_PASS_INT="your_password"

# End-to-End environments (Dune & Titan E2E)
export NSO_USER_E2E="your_username"
export NSO_PASS_E2E="your_password"

# Production environment (Titan Production)
export NSO_USER_PROD="your_username"
export NSO_PASS_PROD="your_password"
```

**Why shell config file?** The `run.sh` script sources these files to load credentials automatically.

**Default Values**: If not set, all credentials default to `admin/admin` (which may not work for all environments).

**After updating your shell config:**
```bash
# Reload your shell configuration
source ~/.zshrc  # or ~/.bashrc or ~/.bash_profile

# Verify variables are set
echo $NSO_USER_INT
```

### SSH Configuration

#### From Local Machine (Windows/macOS/Linux)

You need SSH access configured for:

1. **For Dev/Test/E2E instances**: SSH access to `devm` (jump host)
   ```bash
   # Test connectivity
   ssh devm
   ```

2. **For Production instance**: SSH access to `jump01` on port 443 with MFA
   ```bash
   # Add to ~/.ssh/config
   Host jump01
       HostName opal-jump01.noctools.swissptt.ch
       Port 443
       User your_username
       ControlMaster auto
       ControlPath ~/.ssh/cm-%r@%h:%p
       ControlPersist 10m
   
   # Establish master connection (will prompt for MFA token)
   ssh -fN jump01
   ```

#### From dev-vm Server

- No SSH configuration needed (direct access to NSO instances)
- **Exception**: Titan Production requires jump01 which is not accessible from dev-vm
  - Use your local machine to access Titan Production

### Network Access

The application requires network connectivity to NSO instances:

| Running From | Instances Accessible | Connection Method |
|--------------|---------------------|-------------------|
| **Local Machine** | All 5 instances | SSH tunnels (via devm or jump01) |
| **dev-vm** | 4 instances (all except Titan Production) | Direct TCP/IP access |

### Python Dependencies

Automatically installed by `setup.sh`, but for reference:

```
Django==4.2.27
psutil>=5.9.0  # Cross-platform process management
```

### Optional: Django Admin Account

For accessing Django admin interface (`/admin/`):

```bash
# Create superuser (one-time setup)
python manage.py createsuperuser
```

## Quick Start

### After Git Clone

**On macOS/Linux:**
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

**On Windows (Git Bash or WSL):**
```bash
# 1. Clone the repository
git clone https://github.com/jeremierouzet/taarojek_app.git
cd taarojek_app

# 2. Run setup (one-time)
bash setup.sh

# 3. Start the application
bash run.sh

# 4. View logs (optional)
tail -f logs/nso-manager.log

# 5. Stop the application
bash stop.sh
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

- **Python 3.9+** (works on all platforms)
- **SSH Client**:
  - macOS/Linux: Built-in OpenSSH
  - Windows: OpenSSH Client (install via Settings > Apps > Optional Features)
- **SSH access to devm** (with ProxyJump configuration in `~/.ssh/config`)
- **NSO credentials** in environment variables (optional for development):
  - `NSO_USER_INT` / `NSO_PASS_INT` (for integration)
  - `NSO_USER_E2E` / `NSO_PASS_E2E` (for E2E)
  - `NSO_USER_PROD` / `NSO_PASS_PROD` (for production)

### Platform-Specific Notes

**Windows:**
- Use Git Bash or WSL (Windows Subsystem for Linux) to run shell scripts
- Ensure OpenSSH Client is installed
- Virtual environment activation: `source venv/Scripts/activate`

**macOS/Linux:**
- Native shell support
- Virtual environment activation: `source venv/bin/activate`

### Method 1: Quick Setup (Recommended)

After cloning the repository, simply run:

```bash
./setup.sh
./run.sh
```

### Method 2: Manual Installation

1. **Create and activate virtual environment:**
   
   **macOS/Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
   
   **Windows (Git Bash/PowerShell):**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Git Bash
   # OR
   venv\Scripts\activate.bat     # Command Prompt
   # OR
   venv\Scripts\Activate.ps1     # PowerShell
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

*macOS/Linux:*
```bash
source venv/bin/activate
python manage.py runserver 50478
```

*Windows (Git Bash):*
```bash
source venv/Scripts/activate
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

**macOS/Linux:**
```bash
# View all active tunnels
ps aux | grep "ssh -L"

# Check specific ports using lsof
lsof -i :8888  # Dune Integration
lsof -i :8889  # Titan Integration
lsof -i :8890  # Dune E2E
lsof -i :8891  # Titan E2E
lsof -i :8892  # Titan Production
```

**Windows:**
```bash
# View all SSH processes
tasklist | findstr ssh

# Check specific ports using netstat
netstat -ano | findstr :8888  # Dune Integration
netstat -ano | findstr :8889  # Titan Integration
netstat -ano | findstr :8890  # Dune E2E
netstat -ano | findstr :8891  # Titan E2E
netstat -ano | findstr :8892  # Titan Production
```

### Smart Tunnel Management

The application now features **intelligent tunnel management**:

- **Automatic Detection**: Detects if a tunnel is already running on the required port
- **Auto-Kill**: Automatically kills any existing tunnel on the port before creating a new one
- **Cross-Platform**: Works consistently across Windows, macOS, and Linux
- **No Manual Cleanup**: No need to manually kill tunnels before reconnecting
- **Process Tracking**: Uses `psutil` library for reliable cross-platform process management

**How it works:**
1. When you click "Connect", the app checks if the port is in use
2. If an old tunnel exists, it's automatically terminated
3. A new tunnel is created and tracked
4. The app monitors tunnel health and recreates if needed

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
- **Cross-platform support**: Works on Windows, macOS, and Linux
- **Smart tunnel management**: 
  - Automatically detects existing tunnels on the same port
  - Kills stale tunnels before creating new ones
  - Tracks tunnel processes reliably using `psutil`
- Creates SSH tunnels: `ssh -L LOCAL_PORT:NSO_IP:8888 -N -f devm`
- Each instance uses unique local port (8888-8892)
- Supports multiple simultaneous connections
- Manages tunnel lifecycle (create, check, close)
- Platform-specific process management (handles PID differences between OSes)

**NSO Client** (`device_sync/nso_client.py`)
- REST API integration with NSO
- Device listing and sync checking
- Authentication handling
- SSL verification disabled (for internal use)

**NSO Curl Client** (`device_sync/nso_client_curl.py`)
- Alternative client using curl subprocess
- Bypasses Python requests SSL/TLS issues
- Accepts curl rc=28 (NSO connection behavior)
- Supports GET and POST operations
- Used for device sync checks

**Curl Wrapper** (`device_sync/nso_curl.sh`)
- Standalone bash script for NSO API calls
- Isolates curl from Python environment
- Handles NSO connection timeout gracefully
- Parameters: HOST PORT USERNAME PASSWORD ENDPOINT METHOD DATA

## Recent Updates

### Version 2.1 - Production Support & Performance (January 16, 2026)

**Major Enhancements:**

1. **Fixed Device List Parsing (74 devices now visible!)**
   - ✅ Endpoint changed to `/restconf/data/tailf-ncs:devices?depth=3&fields=device(name)`
   - ✅ Avoids NSO "too many instances: 74" error
   - ✅ All 74 devices from Titan Integration now correctly displayed
   - ✅ Efficient XML parsing with regex patterns

2. **10x Faster Device Sync Checking**
   - ✅ Parallel processing with ThreadPoolExecutor (10 concurrent workers)
   - ✅ Reduced sync check time from ~2 minutes to ~15 seconds for 74 devices
   - ✅ Real-time progress tracking

3. **Production Server Support (jump01)**
   - ✅ Added support for jump01 jump host on port 443
   - ✅ Automatic port selection: 443 for jump01, 22 for devm
   - ✅ HTTP/HTTPS protocol configuration per instance
   - ✅ Titan Production uses HTTP (not HTTPS)

4. **MFA Authentication Support**
   - ✅ SSH ControlMaster integration for jump01
   - ✅ One-time MFA authentication, reused for all tunnels
   - ✅ 10-minute connection persistence (configurable)
   - ✅ Setup: `ssh -fN jump01` (requires MFA token)

5. **Environment Detection**
   - ✅ Auto-detects devm vs local machine
   - ✅ **On devm**: Direct NSO access, no tunnels, no MFA
   - ✅ **On local**: SSH tunnels via jump hosts
   - ✅ Same codebase works everywhere - zero config changes!

6. **Enhanced Error Messages**
   - ✅ Clear SSL/TLS error diagnostics
   - ✅ Connection refused vs timeout differentiation
   - ✅ Server reachability feedback

**Instance Configuration:**

| Instance | Jump Host | SSH Port | Protocol | MFA Required | Local Port |
|----------|-----------|----------|----------|--------------|------------|
| Dune Integration | devm | 22 | HTTPS | No | 8888 |
| Titan Integration | devm | 22 | HTTPS | No | 8889 |
| Dune E2E | devm | 22 | HTTPS | No | 8890 |
| Titan E2E | devm | 22 | HTTPS | No | 8891 |
| **Titan Production** | **jump01** | **443** | **HTTP** | **Yes** | **8892** |

**Setup for Titan Production:**

1. Add to `~/.ssh/config`:
```bash
Host jump01
  ControlMaster auto
  ControlPath ~/.ssh/control-%C
  ControlPersist 10m
```

2. Before using the app:
```bash
# Establish master connection (MFA required once)
ssh -fN jump01

# Verify connection is active
ssh -O check jump01
# Should show: Master running (pid=XXXXX)
```

3. All SSH tunnels reuse this connection for 10 minutes without re-authentication!

**Testing Environment Detection:**
```bash
python3 test_environment_detection.py
```

**Expected behavior:**
- **On devm**: Shows "Running on dev-vm", tunnels disabled, direct NSO access
- **On local**: Shows "Running on local machine", tunnels enabled

**Migration:** No action required - fully backward compatible!

### Version 2.0 - Cross-Platform Support (January 16, 2026)

**Major Enhancements:**

1. **Smart SSH Tunnel Management**
   - ✅ Automatic detection of existing tunnels on the same port
   - ✅ Auto-kill stale tunnels before creating new ones (no manual cleanup!)
   - ✅ Cross-platform process management using `psutil`
   - ✅ Robust PID tracking across Windows, macOS, and Linux

2. **Full Cross-Platform Compatibility**
   - ✅ Windows support (Git Bash/WSL)
   - ✅ macOS native support
   - ✅ Linux native support
   - ✅ Platform-specific virtual environment activation
   - ✅ Unified process and port management

3. **Enhanced Shell Scripts**
   - `setup.sh` - OS detection and platform-specific setup
   - `run.sh` - Cross-platform execution and venv activation
   - `stop.sh` - Platform-aware process termination

4. **Improved User Experience**
   - No need to manually kill existing tunnels
   - Click "Connect" - app handles everything automatically
   - Consistent behavior across all operating systems
   - Better error handling and recovery

**Technical Details:**
- Added `psutil>=5.9.0` for cross-platform process management
- Replaced Unix-specific commands (`lsof`, `pgrep`) with cross-platform equivalents
- Implemented graceful process termination (terminate → wait → kill if needed)
- Enhanced documentation with platform-specific troubleshooting

**Migration:** No action required - fully backward compatible!

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

### Cross-Platform Issues

**Windows: SSH not found**
```bash
# Install OpenSSH Client
# Go to: Settings > Apps > Optional Features > Add a feature
# Search for "OpenSSH Client" and install

# Verify installation
ssh -V
```

**Windows: Scripts won't run**
```bash
# Use Git Bash or WSL
bash setup.sh
bash run.sh

# Or use WSL
wsl ./setup.sh
```

**Windows: Permission denied on scripts**
```bash
# In Git Bash, make scripts executable
chmod +x setup.sh run.sh stop.sh
```

**macOS: Command not found (lsof)**
```bash
# lsof should be pre-installed, but if missing:
# The app now uses psutil which works cross-platform
# Ensure psutil is installed: pip install psutil
```

### Port Already in Use

**macOS/Linux:**
```bash
# Find process using port
sudo lsof -i :50478
kill <PID>

# Or find NSO tunnel ports
sudo lsof -i :8888
```

**Windows:**
```bash
# Find process using port
netstat -ano | findstr :50478
taskkill /PID <PID> /F

# Or find NSO tunnel ports
netstat -ano | findstr :8888
```

### SSH Tunnel Issues

**Problem: Tunnel won't create / Port conflicts**
- **Solution**: The app now **automatically detects and kills** existing tunnels
- Simply click "Connect" again - old tunnels are cleaned up automatically
- No manual intervention needed

**Problem: Connection refused**

*macOS/Linux:*
```bash
# Test SSH access
ssh devm "echo Connection OK"

# Verify NSO instance is running
ssh devm "curl -k https://138.188.202.5:8888"
```

*Windows (Git Bash):*
```bash
# Test SSH access
ssh devm "echo Connection OK"

# Verify NSO instance is running
ssh devm "curl -k https://138.188.202.5:8888"
```

**Problem: Tunnel not created**

*macOS/Linux:*
```bash
# Check active tunnels
ps aux | grep "ssh -L"

# Manual tunnel test
ssh -L 8888:138.188.202.5:8888 -N devm
# Try: curl -k https://localhost:8888
```

*Windows:*
```bash
# Check active tunnels
tasklist | findstr ssh

# Manual tunnel test
ssh -L 8888:138.188.202.5:8888 -N devm
# Try: curl -k https://localhost:8888
```

**Problem: Multiple tunnels conflict**
- **Old behavior**: Had to manually kill conflicting tunnels
- **New behavior**: App automatically detects and kills existing tunnels
- Each NSO instance uses a unique local port (8888-8892)
- Check tunnel status in application UI
- App handles cleanup automatically when reconnecting

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

**Problem: Python requests SSL/TLS timeout errors**
- **Root Cause**: Python's requests library may have SSL/TLS compatibility issues with NSO
- **Solution**: Application uses `nso_client_curl.py` which wraps curl in a subprocess
- **Implementation**: Shell script wrapper (`nso_curl.sh`) bypasses Python SSL issues
- **Note**: Curl exit code 28 (timeout) is accepted if data is received (NSO keeps connections open)

**Problem: "too many instances: 14" error**
- **Root Cause**: NSO REST API limits number of devices returned in single query
- **Solution**: Use `/restconf/data/tailf-ncs:devices?content=config` instead of `/devices/device`
- **Implementation**: `get_all_devices()` now uses correct endpoint with proper XML parsing

**Problem: Curl timeout but operation succeeds**
- **Expected Behavior**: NSO keeps HTTP connections open after sending data
- **Curl Response**: Exit code 28 (operation timeout) with complete data in stdout
- **Not an Error**: Application correctly handles this by checking if data was received
- **Technical Detail**: `nso_client_curl.py` accepts `rc=28` when `stdout` contains data

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
