"""
SSH Tunnel Manager

This module handles creating and managing SSH tunnels to NSO instances.
Cross-platform support for Windows, macOS, and Linux.
"""

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
            time.sleep(1)  # Give OS time to release the port
        
        # Create the SSH tunnel command
        tunnel_spec = f"{local_port}:{nso_ip}:{nso_port}"
        
        # Platform-specific SSH command
        # Note: Removed -f flag, using Popen to background process instead
        # Special handling for jump01: uses port 443 instead of 22
        if ssh_host == 'jump01':
            ssh_port = '443'
        else:
            ssh_port = '22'
        
        if self.os_type == 'Windows':
            # Windows: use ssh.exe (available in Windows 10+)
            cmd = ['ssh', '-p', ssh_port, '-o', 'StrictHostKeyChecking=no', 
                   '-o', 'ServerAliveInterval=60',
                   '-L', tunnel_spec, '-N', ssh_host]
        else:
            # Unix-like (macOS, Linux)
            cmd = ['ssh', '-p', ssh_port, '-o', 'StrictHostKeyChecking=no',
                   '-o', 'ServerAliveInterval=60', 
                   '-L', tunnel_spec, '-N', ssh_host]
        
        logger.info(f"Creating SSH tunnel: {' '.join(cmd)}")
        
        try:
            # Execute the SSH command in background using Popen
            logger.info("Starting SSH tunnel process in background...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True  # Detach from parent process
            )
            
            pid = process.pid
            logger.info(f"SSH process started with PID: {pid}")
            
            # Give the tunnel time to establish - retry multiple times
            logger.info("Waiting for tunnel to establish...")
            max_attempts = 10
            port_ready = False
            
            for attempt in range(max_attempts):
                time.sleep(1)
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
            
            # Verify the tunnel is working by checking if port is in use
            if not port_ready:
                logger.error(
                    f"Port {local_port} not in use after {max_attempts} seconds"
                )
                # Kill the process if it's still running
                try:
                    if process.poll() is None:  # Process still running
                        process.terminate()
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
            logger.exception(f"Error creating tunnel: {e}")
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
            if not self._is_process_running(tunnel_info['pid']):
                stale.append(instance)
        
        for instance in stale:
            del self.active_tunnels[instance]
        
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
            return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False
    
    def _is_port_in_use(self, port):
        """Check if a port is in use - Cross-platform"""
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
            # Fallback: try to bind to the port
            logger.warning(
                f"Access denied checking connections, "
                f"using socket bind test for port {port}"
            )
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('localhost', port))
                sock.close()
                return False  # Port is free (we could bind)
            except OSError:
                return True  # Port in use (bind failed)
        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            # Fallback method using socket
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('localhost', port))
                sock.close()
                return False
            except OSError:
                return True
    
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
        
        return killed_count


# Global tunnel manager instance
tunnel_manager = SSHTunnelManager()
