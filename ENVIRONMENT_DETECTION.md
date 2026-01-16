# Environment Detection - devm vs Local

## How it works

The application automatically detects whether it's running on **devm** or on a **local machine** and adapts its behavior accordingly.

### Detection Logic

```python
# nso_manager/nso_config.py
HOSTNAME = socket.gethostname()
ON_DEVM = 'dev-vm' in HOSTNAME.lower()
USE_TUNNELS = not ON_DEVM
```

## Behavior on devm

When running on devm (hostname contains 'dev-vm'):

✅ **Direct Access Mode**
- `USE_TUNNELS = False` for all instances
- No SSH tunnels created
- Connects directly to NSO servers using their actual IP addresses
- No jump host required
- No MFA required

**Example on devm:**
```bash
# Application connects directly to:
Titan Integration: http://138.188.200.227:8888
Dune Integration: http://138.188.202.5:8888
Titan Production: http://138.188.195.223:8888
# etc.
```

## Behavior on Local Machine

When running locally (hostname does NOT contain 'dev-vm'):

✅ **SSH Tunnel Mode**
- `USE_TUNNELS = True` for all instances
- SSH tunnels created automatically
- Each instance uses a unique local port
- Jump hosts: `devm` (integration/e2e) or `jump01` (production)

**Local Port Mapping:**
- Dune Integration: localhost:8888 → 138.188.202.5:8888 (via devm)
- Titan Integration: localhost:8889 → 138.188.200.227:8888 (via devm)
- Dune E2E: localhost:8890 → 138.188.202.6:8888 (via devm)
- Titan E2E: localhost:8891 → 138.188.200.192:8888 (via devm)
- **Titan Production: localhost:8892 → 138.188.195.223:8888 (via jump01:443)**

### Production Access (jump01)

Titan Production requires MFA authentication via jump01.

**Setup ControlMaster (one-time):**

Add to `~/.ssh/config`:
```
Host jump01
  ControlMaster auto
  ControlPath ~/.ssh/control-%C
  ControlPersist 10m
```

**Before using the app:**
```bash
# Establish master connection (requires MFA token)
ssh -fN jump01

# Verify connection
ssh -O check jump01
# Should show: Master running (pid=XXXXX)
```

This connection remains active for 10 minutes. All SSH tunnels will reuse it without requiring MFA again.

## Testing

Run the environment detection test:

```bash
cd /Users/taarojek/Documents/Swisscom/DEV/taarojek_app
python3 test_environment_detection.py
```

**Expected output on local machine:**
```
🖥️  Current hostname: UM00698
📍 Detected as devm: False
🔌 Tunnels enabled: True
✅ Running on local machine
```

**Expected output on devm:**
```
🖥️  Current hostname: dev-vm-XXX
📍 Detected as devm: True
🔌 Tunnels enabled: False
✅ Running on dev-vm
```

## Instance-Specific Configuration

| Instance | SSH Host | Port | Protocol | MFA |
|----------|----------|------|----------|-----|
| Dune Integration | devm | 22 | HTTPS | No |
| Dune E2E | devm | 22 | HTTPS | No |
| Titan Integration | devm | 22 | HTTPS | No |
| Titan E2E | devm | 22 | HTTPS | No |
| **Titan Production** | **jump01** | **443** | **HTTP** | **Yes** |

## Troubleshooting

### On devm
If tunnels are being created when they shouldn't:
```bash
# Check hostname detection
hostname
# Should contain 'dev-vm'

# Verify in Python
python3 -c "import socket; print('dev-vm' in socket.gethostname().lower())"
# Should print: True
```

### On local machine
If direct access is attempted when tunnels are needed:
```bash
# Check hostname
hostname
# Should NOT contain 'dev-vm'

# For Titan Production, ensure ControlMaster is active:
ssh -O check jump01
```

## Summary

The same codebase works seamlessly on both devm and local machines:
- **devm**: Direct access, no tunnels, no MFA
- **local**: SSH tunnels, automatic port forwarding, jump01 MFA for production

No code changes needed when deploying to devm! 🚀
