"""
NSO Client using curl subprocess

Fallback client that uses curl command instead of Python requests library.
This works around SSL/TLS compatibility issues with Python requests.
"""

import subprocess
import json
import logging

logger = logging.getLogger(__name__)


class NSOClientCurl:
    """Client for interacting with NSO REST API using curl"""
    
    def __init__(self, host='localhost', port=8888, username=None, password=None):
        """
        Initialize NSO client.
        
        Args:
            host (str): NSO host
            port (int): NSO port
            username (str): NSO username
            password (str): NSO password
        """
        self.base_url = f"https://{host}:{port}"
        self.username = username
        self.password = password
    
    def _curl_request(self, endpoint, timeout=10):
        """
        Make a curl request to NSO.
        
        Args:
            endpoint (str): API endpoint path
            timeout (int): Request timeout in seconds
            
        Returns:
            tuple: (success, data/error_message)
        """
        import os
        
        url = f"{self.base_url}{endpoint}"
        
        # Use shell=True to handle special characters in password properly
        cmd = f"curl -k -s --connect-timeout {timeout} -u '{self.username}:{self.password}' '{url}'"
        
        try:
            # Pass current environment to subprocess (includes no_proxy settings)
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout + 2,
                env=os.environ.copy()  # Critical: inherit environment variables
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, f"Curl failed: {result.stderr}"
                
        except subprocess.TimeoutExpired:
            return False, "Request timeout"
        except Exception as e:
            logger.exception(f"Error executing curl: {e}")
            return False, f"Error: {str(e)}"
    
    def test_connection(self):
        """
        Test connection to NSO.
        
        Returns:
            dict: Connection status
        """
        success, data = self._curl_request('/restconf/data/tailf-ncs:devices')
        
        if success:
            # Check if response contains valid XML/JSON
            if '<devices' in data or '"tailf-ncs:devices"' in data:
                return {
                    'success': True,
                    'message': 'Successfully connected to NSO'
                }
            else:
                return {
                    'success': False,
                    'message': f'Unexpected response: {data[:100]}'
                }
        else:
            return {
                'success': False,
                'message': data
            }
    
    def get_all_devices(self):
        """
        Get all devices from NSO.
        
        Returns:
            dict: Result with devices list
        """
        success, data = self._curl_request('/restconf/data/tailf-ncs:devices/device')
        
        if not success:
            return {
                'success': False,
                'message': data,
                'devices': []
            }
        
        devices = []
        
        # Parse XML response (NSO typically returns XML)
        # Simple parsing - look for device names
        import re
        device_names = re.findall(r'<name>([^<]+)</name>', data)
        
        for name in device_names:
            devices.append({'name': name})
        
        return {
            'success': True,
            'devices': devices,
            'count': len(devices)
        }
    
    def check_device_sync(self, device_name):
        """
        Check sync status of a specific device.
        
        Args:
            device_name (str): Device name
            
        Returns:
            dict: Sync status
        """
        endpoint = f'/restconf/data/tailf-ncs:devices/device={device_name}/check-sync'
        success, data = self._curl_request(endpoint)
        
        if not success:
            return {'in_sync': False, 'error': data}
        
        # Parse sync status from response
        in_sync = 'in-sync' in data.lower()
        
        return {
            'in_sync': in_sync,
            'raw_response': data[:200]
        }
    
    def check_all_devices_sync(self):
        """
        Check sync status for all devices.
        
        Returns:
            dict: Sync status for all devices
        """
        # Get all devices
        devices_result = self.get_all_devices()
        
        if not devices_result.get('success'):
            return {
                'success': False,
                'message': devices_result.get('message', 'Failed to get devices'),
                'stats': {'total': 0, 'in_sync': 0, 'out_of_sync': 0},
                'devices': []
            }
        
        devices = devices_result.get('devices', [])
        
        # Check sync for each device
        device_status = []
        in_sync_count = 0
        out_of_sync_count = 0
        
        for device in devices:
            name = device.get('name')
            sync_status = self.check_device_sync(name)
            
            is_in_sync = sync_status.get('in_sync', False)
            if is_in_sync:
                in_sync_count += 1
            else:
                out_of_sync_count += 1
            
            device_status.append({
                'name': name,
                'in_sync': is_in_sync
            })
        
        return {
            'success': True,
            'message': f'Checked {len(devices)} devices',
            'stats': {
                'total': len(devices),
                'in_sync': in_sync_count,
                'out_of_sync': out_of_sync_count
            },
            'devices': device_status
        }
