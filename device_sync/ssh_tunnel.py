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
        if self.os_type == 'Windows':
            # Windows: use ssh.exe (available in Windows 10+)
            cmd = ['ssh', '-L', tunnel_spec, '-N', '-f', ssh_host]
        else:
            # Unix-like (macOS, Linux)
            cmd = ['ssh', '-L', tunnel_spec, '-N', '-f', ssh_host]
        
        try:
            # Execute the SSH command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                logger.error(f"Failed to create tunnel: {result.stderr}")
                return {
                    'success': False,
                    'message': f'Failed to create tunnel: {result.stderr}'
                }
            
            # Give the tunnel a moment to establish
            time.sleep(2)
            
            # Find the PID of the tunnel
            pid = self._find_tunnel_pid(local_port, nso_ip, nso_port)
            
            if pid:
                self.active_tunnels[instance_name] = {'pid': pid, 'local_port': local_port}
                logger.info(f"Created tunnel to {instance_name} on port {local_port}, PID: {pid}")
                return {
                    'success': True,
                    'message': f'Tunnel created on port {local_port}',
                    'pid': pid,
                    'local_port': local_port,
                    'url': f'https://localhost:{local_port}'
                }
            else:
                # Tunnel might be running but hard to find PID, check if port is in use
                if self._is_port_in_use(local_port):
                    logger.warning(f"Tunnel appears to be running on port {local_port} but PID not found")
                    # Try one more time to find PID
                    time.sleep(1)
                    pid = self._find_tunnel_pid_by_port(local_port)
                    if pid:
                        self.active_tunnels[instance_name] = {'pid': pid, 'local_port': local_port}
                        return {
                            'success': True,
                            'message': f'Tunnel created on port {local_port}',
                            'pid': pid,
                            'local_port': local_port,
                            'url': f'https://localhost:{local_port}'
                        }
                    else:
                        # Port is in use, assume tunnel is working even without PID
                        self.active_tunnels[instance_name] = {'pid': -1, 'local_port': local_port}
                        return {
                            'success': True,
                            'message': f'Tunnel created on port {local_port} (PID tracking unavailable)',
                            'pid': -1,
                            'local_port': local_port,
                            'url': f'https://localhost:{local_port}'
                        }
                
                return {
                    'success': False,
                    'message': 'Tunnel process not found after creation'
                }
                
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': 'SSH tunnel creation timed out'
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
            for conn in psutil.net_connections(kind='inet'):
                if conn.laddr.port == port:
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
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
        
        return killed_count


# Global tunnel manager instance
tunnel_manager = SSHTunnelManager()
