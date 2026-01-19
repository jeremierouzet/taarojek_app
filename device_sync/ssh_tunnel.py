"""
SSH Tunnel Manager

This module handles creating and managing SSH tunnels to NSO instances.
Cross-platform support for Windows, macOS, and Linux.
"""

import os
import subprocess
import time
import logging
import platform
import psutil

logger = logging.getLogger(__name__)


class SSHTunnelManager:
    """Manages SSH tunnels to NSO instances - Cross-platform"""
    
    def __init__(self):
        self.active_tunnels = {}  # instance_name -> {'pid': int, 'local_port': int}
        self.os_type = platform.system()  # 'Windows', 'Linux', 'Darwin' (macOS)
    
    def test_remote_reachability(self, nso_ip, nso_port, ssh_host='devm', timeout=3):
        """
        Test if a remote NSO server is reachable from the SSH jump host.
        
        Args:
            nso_ip (str): IP address of the NSO server
            nso_port (int): Port of the NSO server
            ssh_host (str): SSH host to test from (default: 'devm')
            timeout (int): Timeout in seconds (default: 3)
            
        Returns:
            dict: {'reachable': bool, 'message': str}
        """
        logger.info(f"Testing reachability of {nso_ip}:{nso_port} from {ssh_host}...")
        
        # Use nc (netcat) to test connectivity via SSH
        cmd = ['ssh', ssh_host, f'nc -zv -w{timeout} {nso_ip} {nso_port} 2>&1']
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )
            
            # nc returns 0 if connection successful
            if result.returncode == 0:
                logger.info(f"Server {nso_ip}:{nso_port} is reachable from {ssh_host}")
                return {
                    'reachable': True,
                    'message': f'Server {nso_ip}:{nso_port} is reachable'
                }
            else:
                # Parse error message
                output = result.stdout + result.stderr
                if 'refused' in output.lower():
                    msg = f"Server {nso_ip}:{nso_port} is refusing connections (server may be down or port closed)"
                elif 'timeout' in output.lower() or 'timed out' in output.lower():
                    msg = f"Connection to {nso_ip}:{nso_port} timed out (server unreachable or firewalled)"
                else:
                    msg = f"Cannot reach {nso_ip}:{nso_port} from {ssh_host}: {output[:100]}"
                
                logger.warning(msg)
                return {
                    'reachable': False,
                    'message': msg
                }
                
        except subprocess.TimeoutExpired:
            msg = f"Timeout testing connectivity to {nso_ip}:{nso_port} from {ssh_host}"
            logger.error(msg)
            return {
                'reachable': False,
                'message': msg
            }
        except Exception as e:
            msg = f"Error testing reachability: {str(e)}"
            logger.exception(msg)
            return {
                'reachable': False,
                'message': msg
            }
    
    def create_tunnel(self, instance_name, nso_ip, nso_port, local_port=8888, ssh_host='devm'):
        """
        Create an SSH tunnel to an NSO instance.
        Automatically detects and kills existing tunnels on the same port.
        
        Args:
            instance_name (str): Name of the NSO instance
            nso_ip (str): IP address of the NSO server
            nso_port (int): Port of the NSO server
            local_port (int): Local port to bind to (default: 8888)
            ssh_host (str): SSH host to tunnel through (default: 'devm')
            
        Returns:
            dict: Status of the tunnel creation
        """
        # Check if tunnel already exists for this instance
        if instance_name in self.active_tunnels:
            tunnel_info = self.active_tunnels[instance_name]
            pid = tunnel_info['pid']
            stored_port = tunnel_info['local_port']
            
            if self._is_process_running(pid):
                # Check if it's still the right tunnel
                if stored_port == local_port and self._is_port_in_use(local_port):
                    return {
                        'success': True,
                        'message': f'Tunnel to {instance_name} already active',
                        'pid': pid,
                        'local_port': stored_port
                    }
                else:
                    # Tunnel configuration changed or died, kill and recreate
                    logger.info(f"Tunnel configuration changed for {instance_name}, recreating...")
                    self._kill_process(pid)
                    del self.active_tunnels[instance_name]
            else:
                # Clean up stale entry
                del self.active_tunnels[instance_name]
        
        # Kill any existing tunnels using this local port
        logger.info(f"Checking for existing tunnels on port {local_port}...")
        killed = self._kill_tunnel_on_port(local_port)
        if killed:
            logger.info(f"Killed {killed} existing process(es) on port {local_port}")
            time.sleep(2)  # Give OS time to release the port
        
        # Double-check the port is actually free
        if self._is_port_in_use(local_port):
            logger.warning(f"Port {local_port} still in use after cleanup, attempting force close...")
            # Try one more aggressive cleanup
            import socket
            try:
                # Try to bind to ensure it's really free
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_sock.bind(('localhost', local_port))
                test_sock.close()
                time.sleep(1)
            except OSError:
                # Still in use, try killing by port one more time
                self._kill_tunnel_on_port(local_port)
                time.sleep(2)
        
        # Create the SSH tunnel command
        tunnel_spec = f"{local_port}:{nso_ip}:{nso_port}"
        
        # Platform-specific SSH command
        # For jump01: uses port 443 and relies on ControlMaster
        # Use -f flag to let SSH handle backgrounding properly
        if ssh_host == 'jump01':
            ssh_port = '443'
            # For jump01, let SSH config handle ControlMaster
            # Use -f to background after authentication (works with ControlMaster)
            ssh_cmd_base = ['ssh', '-f', '-p', ssh_port,
                           '-o', 'StrictHostKeyChecking=no', 
                           '-o', 'ServerAliveInterval=60',
                           '-o', 'ConnectTimeout=10',  # Limit connection attempt time
                           '-o', 'ExitOnForwardFailure=yes']  # Exit if port forwarding fails
        else:
            ssh_port = '22'
            ssh_cmd_base = ['ssh', '-f', '-p', ssh_port,
                           '-o', 'StrictHostKeyChecking=no',
                           '-o', 'ServerAliveInterval=60',
                           '-o', 'ConnectTimeout=10',  # Limit connection attempt time
                           '-o', 'ExitOnForwardFailure=yes']
        
        if self.os_type == 'Windows':
            # Windows: use ssh.exe (available in Windows 10+)
            cmd = ssh_cmd_base + ['-L', tunnel_spec, '-N', ssh_host]
        else:
            # Unix-like (macOS, Linux)
            cmd = ssh_cmd_base + ['-L', tunnel_spec, '-N', ssh_host]
        
        logger.info(f"Creating SSH tunnel: {' '.join(cmd)}")
        
        # For jump01, verify ControlMaster is available first
        if ssh_host == 'jump01':
            test_cmd = ['ssh', '-O', 'check', ssh_host]
            try:
                test_result = subprocess.run(
                    test_cmd,
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if test_result.returncode != 0:
                    logger.warning(f"ControlMaster check failed: {test_result.stderr}")
                    return {
                        'success': False,
                        'message': (
                            'No active SSH ControlMaster connection to jump01. '
                            'Please connect first: ssh jump01'
                        )
                    }
                else:
                    logger.info("ControlMaster connection verified")
            except Exception as e:
                logger.warning(f"ControlMaster check error: {e}")
        
        # Use different methods for jump01 (with -f) vs others (with Popen)
        if ssh_host == 'jump01':
            return self._create_tunnel_with_f_flag(cmd, instance_name, local_port, nso_ip, nso_port, ssh_host)
        else:
            return self._create_tunnel_with_popen(cmd, instance_name, local_port, nso_ip, nso_port)
    
    def _create_tunnel_with_f_flag(self, cmd, instance_name, local_port, nso_ip, nso_port, ssh_host):
        """Create tunnel using SSH -f flag (for jump01 with ControlMaster)"""
        try:
            # Execute the SSH command - using -f flag so SSH handles backgrounding
            logger.info("Starting SSH tunnel process with -f flag...")
            # Set TERM environment variable to prevent tput errors from shell rc files
            env = os.environ.copy()
            env['TERM'] = 'dumb'
            
            # Use run() with -f flag which backgrounds after establishing connection
            timeout_duration = 15
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=timeout_duration
            )
            
            if result.returncode != 0:
                # SSH failed to start
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                # Filter out tput warnings
                error_lines = [line for line in error_msg.split('\n') 
                              if line and not line.startswith('tput:')]
                filtered_error = '\n'.join(error_lines).strip()
                
                if filtered_error:
                    logger.error(f"SSH command failed: {filtered_error}")
                    
                    if 'Permission denied' in filtered_error:
                        return {
                            'success': False,
                            'message': (
                                'SSH authentication failed for jump01 (requires 2FA). '
                                'Please establish an SSH connection first: ssh jump01'
                            )
                        }
                    
                    return {
                        'success': False,
                        'message': f'SSH tunnel failed: {filtered_error[:200]}'
                    }
                else:
                    # Only tput errors, might still work
                    logger.warning("SSH returned non-zero but only tput warnings")
            
            logger.info(f"SSH tunnel command completed, finding PID...")
            
            # Find the SSH process PID (since -f backgrounds it)
            # Give it a moment to show up in process list
            time.sleep(2)
            
            # Try multiple methods to find the PID
            pid = None
            for attempt in range(5):
                pid = self._find_tunnel_pid(local_port, nso_ip, nso_port)
                if pid:
                    logger.info(f"Found tunnel by command line match (PID: {pid})")
                    break
                
                # Fallback: find by port
                pid = self._find_tunnel_pid_by_port(local_port)
                if pid:
                    logger.info(f"Found tunnel by port (PID: {pid})")
                    break
                
                # Wait and retry
                if attempt < 4:
                    logger.debug(f"PID not found yet, retrying... (attempt {attempt + 1}/5)")
                    time.sleep(1)
            
            if not pid or pid <= 0:
                # Last attempt: use lsof to find process on port
                try:
                    result = subprocess.run(
                        ['lsof', '-ti', f':{local_port}'],
                        capture_output=True,
                        text=True,
                        timeout=2
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pid = int(result.stdout.strip().split('\n')[0])
                        logger.info(f"Found tunnel via lsof (PID: {pid})")
                except Exception as e:
                    logger.warning(f"lsof fallback failed: {e}")
            
            if not pid or pid <= 0:
                logger.warning("Could not find SSH tunnel process, but may still work")
                # Don't fail here - the tunnel might still be working
                # Just use a dummy PID and rely on port checking
                pid = -1
            
            logger.info(f"Found SSH tunnel with PID: {pid}")
            
            # Verify port is in use
            return self._verify_and_finalize_tunnel(instance_name, local_port, pid)
                
        except subprocess.TimeoutExpired:
            logger.error(f"SSH command timed out")
            return {
                'success': False,
                'message': (
                    f'SSH connection to {ssh_host} timed out. '
                    f'Please verify network connectivity and that {ssh_host} is reachable.'
                )
            }
        except Exception as e:
            logger.exception(f"Error creating tunnel: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def _create_tunnel_with_popen(self, cmd, instance_name, local_port, nso_ip, nso_port):
        """Create tunnel using Popen (for devm and other standard SSH hosts)"""
        try:
            # Remove -f flag from command for Popen
            cmd_no_f = [arg for arg in cmd if arg != '-f']
            
            logger.info("Starting SSH tunnel with Popen...")
            env = os.environ.copy()
            env['TERM'] = 'dumb'
            
            process = subprocess.Popen(
                cmd_no_f,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                env=env
            )
            
            pid = process.pid
            logger.info(f"SSH process started with PID: {pid}")
            
            # Verify port is in use
            return self._verify_and_finalize_tunnel(instance_name, local_port, pid)
            
        except Exception as e:
            logger.exception(f"Error creating tunnel: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def _verify_and_finalize_tunnel(self, instance_name, local_port, pid):
        """Verify tunnel is working and finalize setup"""
        try:
            # Give the tunnel time to establish and verify
            logger.info("Waiting for tunnel to establish...")
            max_attempts = 15
            port_ready = False
            
            time.sleep(2)  # Initial delay
            
            for attempt in range(max_attempts):
                if self._is_port_in_use(local_port):
                    port_ready = True
                    logger.info(
                        f"Port {local_port} is now in use "
                        f"(attempt {attempt + 1}/{max_attempts})"
                    )
                    break
                logger.info(
                    f"Attempt {attempt + 1}/{max_attempts}: "
                    f"Port {local_port} not ready yet..."
                )
                time.sleep(1)
            
            # Verify the tunnel is working by checking if port is in use
            if not port_ready:
                logger.error(
                    f"Port {local_port} not in use after {max_attempts + 2} seconds"
                )
                # Kill the process if we found it
                if pid > 0:
                    try:
                        self._kill_process(pid)
                        logger.info(f"Terminated SSH process {pid}")
                    except Exception as e:
                        logger.warning(f"Error terminating process: {e}")
                
                return {
                    'success': False,
                    'message': (
                        'Tunnel failed to bind to local port. '
                        'Check SSH configuration and network connectivity.'
                    )
                }
            
            logger.info(f"Tunnel successfully established on port {local_port}")
            self.active_tunnels[instance_name] = {
                'pid': pid, 
                'local_port': local_port
            }
            
            return {
                'success': True,
                'message': f'Tunnel created on port {local_port}',
                'pid': pid,
                'local_port': local_port,
                'url': f'https://localhost:{local_port}'
            }
        except Exception as e:
            logger.exception(f"Error verifying tunnel: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def close_tunnel(self, instance_name):
        """
        Close an SSH tunnel.
        
        Args:
            instance_name (str): Name of the NSO instance
            
        Returns:
            dict: Status of the tunnel closure
        """
        if instance_name not in self.active_tunnels:
            return {
                'success': False,
                'message': f'No active tunnel found for {instance_name}'
            }
        
        tunnel_info = self.active_tunnels[instance_name]
        pid = tunnel_info['pid']
        local_port = tunnel_info['local_port']
        
        try:
            # Kill the process
            if pid > 0:
                self._kill_process(pid)
            else:
                # PID not tracked, kill by port
                self._kill_tunnel_on_port(local_port)
            
            del self.active_tunnels[instance_name]
            logger.info(
                f"Closed tunnel to {instance_name}, "
                f"PID: {pid}, Port: {local_port}"
            )
            return {
                'success': True,
                'message': 'Tunnel closed successfully'
            }
        except Exception as e:
            logger.exception(f"Error closing tunnel: {e}")
            # Try to clean up anyway
            if instance_name in self.active_tunnels:
                del self.active_tunnels[instance_name]
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def get_active_tunnels(self):
        """
        Get list of active tunnels.
        
        Returns:
            dict: Active tunnels with their info (pid and local_port)
        """
        # Clean up stale entries
        stale = []
        for instance, tunnel_info in self.active_tunnels.items():
            pid = tunnel_info['pid']
            is_running = self._is_process_running(pid)
            logger.debug(f"Checking tunnel {instance}: PID={pid}, running={is_running}")
            if not is_running:
                stale.append(instance)
        
        for instance in stale:
            logger.info(f"Removing stale tunnel: {instance}")
            del self.active_tunnels[instance]
        
        logger.debug(f"Active tunnels: {list(self.active_tunnels.keys())}")
        return self.active_tunnels.copy()
    
    def get_tunnel_port(self, instance_name):
        """
        Get the local port for an active tunnel.
        
        Args:
            instance_name (str): Name of the NSO instance
            
        Returns:
            int: Local port number or None if tunnel not active
        """
        if instance_name in self.active_tunnels:
            return self.active_tunnels[instance_name]['local_port']
        return None
    
    def _find_tunnel_pid(self, local_port, nso_ip, nso_port):
        """Find the PID of an SSH tunnel process - Cross-platform"""
        try:
            # Use psutil for cross-platform process finding
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if not cmdline:
                        continue
                    
                    # Check if it's an SSH process
                    if 'ssh' not in proc.info['name'].lower():
                        continue
                    
                    # Look for our tunnel specification in the command line
                    cmdline_str = ' '.join(cmdline)
                    tunnel_spec = f"{local_port}:{nso_ip}:{nso_port}"
                    
                    if tunnel_spec in cmdline_str:
                        return proc.info['pid']
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            logger.error(f"Error finding tunnel PID: {e}")
        
        return None
    
    def _find_tunnel_pid_by_port(self, port):
        """Find PID using a specific port - Cross-platform"""
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.status == 'LISTEN':
                    return conn.pid
        except Exception as e:
            logger.error(f"Error finding PID by port: {e}")
        
        return None
    
    def _is_process_running(self, pid):
        """Check if a process is running - Cross-platform"""
        if pid <= 0:
            return False
        
        try:
            # First check if PID exists (lightweight check)
            if not psutil.pid_exists(pid):
                return False
            
            # Try to get process info
            proc = psutil.Process(pid)
            return proc.is_running()
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            # On macOS, we might not have permission to inspect the process
            # But if pid_exists returned True, the process is likely running
            # Do a secondary check using ps command
            import subprocess
            try:
                result = subprocess.run(
                    ['ps', '-p', str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                # ps returns 0 if process exists
                return result.returncode == 0
            except:
                # Fallback: assume running if pid exists
                return psutil.pid_exists(pid)
    
    def _is_port_in_use(self, port):
        """Check if a port is in use - Cross-platform"""
        # Try psutil first (works on most platforms with proper permissions)
        try:
            connections = psutil.net_connections(kind='inet')
            for conn in connections:
                try:
                    if conn.laddr.port == port:
                        return True
                except (AttributeError, IndexError):
                    continue
            return False
        except psutil.AccessDenied:
            # macOS often denies access, use socket fallback
            pass
        except Exception as e:
            logger.debug(f"psutil error checking port {port}: {e}")
        
        # Fallback: try to connect to the port (more reliable than bind test)
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            # Try to connect to the port
            result = sock.connect_ex(('localhost', port))
            sock.close()
            # If connection succeeds or is refused, port is in use
            # connect_ex returns 0 on success, errno on failure
            if result == 0:
                return True  # Connection successful, port in use
            elif result == 61:  # Connection refused (macOS/Linux)
                return True  # Service is listening but refused connection
            elif result == 111:  # Connection refused (Linux)
                return True
            # For SSH tunnels, try bind test as secondary check
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.settimeout(0.5)
            try:
                sock2.bind(('localhost', port))
                sock2.close()
                return False  # Could bind, port is free
            except OSError:
                return True  # Bind failed, port in use
        except Exception as e:
            logger.debug(f"Socket test error for port {port}: {e}")
            # Final fallback: assume port might be in use if we can't test
            return False
    
    def _kill_process(self, pid):
        """Kill a process - Cross-platform"""
        if pid <= 0:
            return
        
        try:
            proc = psutil.Process(pid)
            proc.terminate()  # Try graceful termination first
            
            # Wait up to 3 seconds for process to terminate
            try:
                proc.wait(timeout=3)
            except psutil.TimeoutExpired:
                # Force kill if still running
                proc.kill()
                
            logger.info(f"Killed process {pid}")
        except psutil.NoSuchProcess:
            logger.debug(f"Process {pid} already terminated")
        except psutil.AccessDenied:
            logger.error(f"Access denied when trying to kill process {pid}")
        except Exception as e:
            logger.error(f"Error killing process {pid}: {e}")
    
    def _kill_tunnel_on_port(self, port):
        """Kill any SSH tunnel already using the specified local port - Cross-platform"""
        killed_count = 0
        
        try:
            # Find all connections using this port
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port and conn.pid:
                    try:
                        proc = psutil.Process(conn.pid)
                        
                        # Verify it's an SSH process
                        if 'ssh' in proc.name().lower():
                            logger.info(f"Killing existing SSH tunnel on port {port} (PID: {conn.pid})")
                            self._kill_process(conn.pid)
                            killed_count += 1
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
        except Exception as e:
            logger.debug(f"Error checking for processes on port {port}: {e}")
        
        # Fallback for macOS: use lsof to find process using the port
        if killed_count == 0:
            try:
                import subprocess
                result = subprocess.run(
                    ['lsof', '-ti', f':{port}'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid_str in pids:
                        try:
                            pid = int(pid_str)
                            proc = psutil.Process(pid)
                            if 'ssh' in proc.name().lower():
                                logger.info(f"Killing SSH tunnel on port {port} via lsof (PID: {pid})")
                                self._kill_process(pid)
                                killed_count += 1
                        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
            except Exception as e:
                logger.debug(f"lsof fallback failed for port {port}: {e}")
        
        return killed_count


# Global tunnel manager instance
tunnel_manager = SSHTunnelManager()
