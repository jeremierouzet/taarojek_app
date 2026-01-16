"""
SSH Tunnel Manager

This module handles creating and managing SSH tunnels to NSO instances.
"""

import subprocess
import time
import signal
import logging

logger = logging.getLogger(__name__)


class SSHTunnelManager:
    """Manages SSH tunnels to NSO instances"""
    
    def __init__(self):
        self.active_tunnels = {}  # instance_name -> {'pid': int, 'local_port': int}
    
    def create_tunnel(self, instance_name, nso_ip, nso_port, local_port=8888, ssh_host='devm'):
        """
        Create an SSH tunnel to an NSO instance.
        
        Args:
            instance_name (str): Name of the NSO instance
            nso_ip (str): IP address of the NSO server
            nso_port (int): Port of the NSO server
            local_port (int): Local port to bind to (default: 8888)
            ssh_host (str): SSH host to tunnel through (default: 'devm')
            
        Returns:
            dict: Status of the tunnel creation
        """
        # Check if tunnel already exists
        if instance_name in self.active_tunnels:
            tunnel_info = self.active_tunnels[instance_name]
            pid = tunnel_info['pid']
            stored_port = tunnel_info['local_port']
            
            if self._is_process_running(pid):
                return {
                    'success': True,
                    'message': f'Tunnel to {instance_name} already active',
                    'pid': pid,
                    'local_port': stored_port
                }
            else:
                # Clean up stale entry
                del self.active_tunnels[instance_name]
        
        # No need to kill existing tunnels - each instance has unique port
        
        # Create the SSH tunnel command
        tunnel_spec = f"{local_port}:{nso_ip}:{nso_port}"
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
            time.sleep(1)
            
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
            subprocess.run(['kill', str(pid)], check=True)
            del self.active_tunnels[instance_name]
            logger.info(f"Closed tunnel to {instance_name}, PID: {pid}, Port: {local_port}")
            return {
                'success': True,
                'message': f'Tunnel closed successfully'
            }
        except Exception as e:
            logger.exception(f"Error closing tunnel: {e}")
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
        """Find the PID of an SSH tunnel process"""
        try:
            # Search for the SSH process with our tunnel spec
            search_pattern = f"{local_port}:{nso_ip}:{nso_port}"
            result = subprocess.run(
                ['pgrep', '-f', search_pattern],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return int(result.stdout.strip().split('\n')[0])
        except Exception as e:
            logger.error(f"Error finding tunnel PID: {e}")
        
        return None
    
    def _is_process_running(self, pid):
        """Check if a process is running"""
        try:
            # Send signal 0 to check if process exists
            subprocess.run(['kill', '-0', str(pid)], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def _kill_tunnel_on_port(self, port):
        """Kill any SSH tunnel already using the specified local port"""
        try:
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        subprocess.run(['kill', pid], check=True)
                        logger.info(f"Killed existing process {pid} on port {port}")
                    except Exception as e:
                        logger.warning(f"Could not kill process {pid}: {e}")
        except Exception as e:
            logger.debug(f"No processes found on port {port}: {e}")


# Global tunnel manager instance
tunnel_manager = SSHTunnelManager()
