# Cross-Platform Update - Changelog

## Summary
Updated taarojek_app to be fully cross-platform (Windows, macOS, Linux) with intelligent SSH tunnel management.

## Date
January 16, 2026

## Major Changes

### 1. SSH Tunnel Manager (`device_sync/ssh_tunnel.py`)

**Previous Behavior:**
- Linux/macOS specific commands (`lsof`, `pgrep`, `kill`)
- Manual cleanup required for stale tunnels
- Port conflicts could occur

**New Behavior:**
- ✅ **Cross-platform support** using `psutil` library
- ✅ **Automatic tunnel detection** - finds existing tunnels on the same port
- ✅ **Auto-kill stale tunnels** - terminates old tunnels before creating new ones
- ✅ **Robust process management** - handles PIDs correctly across all platforms
- ✅ **Smart reconnection** - no manual cleanup needed

**Key Features:**
```python
def create_tunnel():
    # 1. Detects existing tunnels on the port
    # 2. Kills them automatically
    # 3. Creates new tunnel
    # 4. Tracks process reliably
```

**Platform-Specific Implementations:**
- Windows: Uses `tasklist`, `taskkill`, `netstat`
- macOS/Linux: Uses standard Unix tools as fallback
- All platforms: Primary method uses `psutil` for consistency

### 2. Shell Scripts

#### `setup.sh`
- Detects OS type (Windows/macOS/Linux)
- Provides platform-specific instructions
- Warns about OpenSSH requirement on Windows

#### `run.sh`
- Cross-platform virtual environment activation
  - Windows: `venv/Scripts/activate`
  - Unix: `venv/bin/activate`
- Reads credentials from multiple shell configs (`.zshrc`, `.bashrc`, `.bash_profile`)
- Platform-specific background execution

#### `stop.sh`
- Cross-platform process termination
  - Windows: `taskkill`
  - Unix: `kill`
- Platform-specific port checking
  - Windows: `netstat`
  - Unix: `lsof` or `netstat`

### 3. Dependencies (`requirements.txt`)

**Added:**
```
psutil>=5.9.0  # Cross-platform process and system utilities
```

**Purpose:**
- Consistent process management across all platforms
- Reliable port checking
- Cross-platform PID tracking

### 4. Documentation (`README.md`)

**New Sections:**
- Cross-platform setup instructions
- Platform-specific prerequisites
- Windows-specific notes (OpenSSH, Git Bash/WSL)
- Smart Tunnel Management explanation
- Cross-platform troubleshooting guide

**Updated Sections:**
- Features list (added cross-platform bullets)
- Quick Start (separate Windows/macOS/Linux instructions)
- Prerequisites (SSH client requirements)
- Troubleshooting (platform-specific commands)

## Benefits

### For Users
1. **No Manual Cleanup**: Click "Connect" - old tunnels are automatically cleaned up
2. **Works Everywhere**: Windows, macOS, Linux all supported
3. **More Reliable**: Better process tracking and error handling
4. **Less Frustration**: No more "port already in use" errors

### For Developers
1. **Consistent Behavior**: Same functionality across all platforms
2. **Better Testing**: Can develop on any OS
3. **Maintainable**: Uses standard library (`psutil`) instead of platform-specific commands
4. **Robust**: Handles edge cases (zombie processes, port conflicts, etc.)

## Migration Guide

### For Existing Users

**No changes required!** The app is backward compatible.

Just update and run:
```bash
git pull
./setup.sh  # Updates dependencies (adds psutil)
./run.sh    # Works as before, but better!
```

### For New Windows Users

1. Install OpenSSH Client (Windows 10+):
   - Settings > Apps > Optional Features > OpenSSH Client

2. Clone and run using Git Bash or WSL:
   ```bash
   git clone <repo>
   cd taarojek_app
   bash setup.sh
   bash run.sh
   ```

## Technical Details

### Process Detection
```python
# Old method (Unix-only):
subprocess.run(['pgrep', '-f', search_pattern])

# New method (Cross-platform):
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    if tunnel_spec in ' '.join(proc.info['cmdline']):
        return proc.info['pid']
```

### Port Checking
```python
# Old method (Unix-only):
subprocess.run(['lsof', '-ti', f':{port}'])

# New method (Cross-platform):
for conn in psutil.net_connections(kind='inet'):
    if conn.laddr.port == port:
        return True
```

### Process Termination
```python
# Old method (Unix-only):
subprocess.run(['kill', str(pid)])

# New method (Cross-platform):
proc = psutil.Process(pid)
proc.terminate()  # Graceful
proc.wait(timeout=3)
if still_running:
    proc.kill()  # Force kill
```

## Testing Recommendations

### Before Deployment
1. Test on Windows (Git Bash/WSL)
2. Test on macOS
3. Test on Linux (dev-vm)
4. Verify tunnel auto-cleanup works
5. Test multiple simultaneous connections
6. Test reconnection scenarios

### Test Scenarios
- [ ] Create tunnel
- [ ] Tunnel already exists (should auto-kill and recreate)
- [ ] Multiple instances simultaneously
- [ ] Disconnect and reconnect
- [ ] App restart with tunnels active
- [ ] Port conflict resolution

## Known Issues / Limitations

1. **Windows SSH**: Requires OpenSSH Client to be installed
2. **Git Bash Recommended**: On Windows, Git Bash provides better compatibility than PowerShell
3. **WSL Alternative**: Can also use WSL on Windows for full Unix compatibility

## Future Enhancements

Potential future improvements:
- [ ] GUI-based setup for Windows users
- [ ] Automatic SSH config setup
- [ ] Tunnel health monitoring dashboard
- [ ] Auto-reconnect on tunnel failure
- [ ] Native Windows service support (instead of bash scripts)

## Files Modified

- `device_sync/ssh_tunnel.py` - Complete rewrite with cross-platform support
- `requirements.txt` - Added psutil dependency
- `setup.sh` - Cross-platform detection and instructions
- `run.sh` - Cross-platform execution
- `stop.sh` - Cross-platform process termination
- `README.md` - Comprehensive cross-platform documentation

## Files Added

- `CHANGELOG_CROSS_PLATFORM.md` - This file

## Contributors

- Initial dev-vm implementation: Jérémie Rouzet (taarojek)
- Cross-platform update: AI Assistant (Jan 16, 2026)
