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
    
    def _curl_request(self, endpoint, timeout=10, method='GET', data=None):
        """
        Make a curl request to NSO.
        
        Args:
            endpoint (str): API endpoint path
            timeout (int): Request timeout in seconds
            method (str): HTTP method - GET or POST
            data (str): POST data (JSON string)
            
        Returns:
            tuple: (success, data/error_message)
        """
        import os
        from pathlib import Path
        
        # Get the directory where this script is located
        script_dir = Path(__file__).parent
        wrapper_script = script_dir / "nso_curl.sh"
        
        # Extract host and port from base_url
        # Format: https://host:port
        url_parts = self.base_url.replace('https://', '').replace('http://', '')
        if ':' in url_parts:
            host, port = url_parts.split(':')
        else:
            host = url_parts
            port = '8888'
        
        # Call wrapper script directly
        cmd = [
            str(wrapper_script),
            host,
            port,
            self.username,
            self.password,
            endpoint,
            method
        ]
        
        # Add data if POST
        if data:
            cmd.append(data)
        
        try:
            logger.debug(f"Calling wrapper: {wrapper_script} {host}:{port} {endpoint} {method}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 2
            )
            
            logger.debug(f"Return code: {result.returncode}, Output length: {len(result.stdout)}, Stderr: {result.stderr[:200]}")
            
            # rc=0 or rc=28 (timeout) with data is OK
            # NSO sometimes keeps connection open causing curl timeout, but data is received
            if (result.returncode == 0 or result.returncode == 28) and result.stdout:
                return True, result.stdout
            else:
                error_msg = result.stderr if result.stderr else "No output"
                return False, f"Curl failed (rc={result.returncode}): {error_msg}"
                
        except subprocess.TimeoutExpired as e:
            logger.error(f"Curl timeout after {timeout + 2}s for {endpoint}")
            return False, f"Request timeout (>{timeout}s)"
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
        # Use /devices endpoint instead of /devices/device to avoid "too many instances" error
        success, data = self._curl_request('/restconf/data/tailf-ncs:devices?content=config', timeout=15)
        
        if not success:
            return {
                'success': False,
                'message': data,
                'devices': []
            }
        
        devices = []
        
        # Parse XML response - extract device names
        # Look for <device><name>xxx</name> pattern
        import re
        # Match device blocks and extract names
        device_pattern = r'<device>\s*<name>([^<]+)</name>'
        device_names = re.findall(device_pattern, data)
        
        for name in device_names:
            devices.append({'name': name})
        
        return {
            'success': True,
            'devices': devices,
            'count': len(devices)
        }
    
    def check_device_sync(self, device_name):
        """
        Check sync status of a specific device using NSO check-sync operation.
        
        Args:
            device_name (str): Device name
            
        Returns:
            dict: Sync status
        """
        # Use NSO operational endpoint with POST
        endpoint = f'/restconf/operations/tailf-ncs:devices/device={device_name}/check-sync'
        post_data = '{}'  # Empty JSON object for the operation
        
        success, data = self._curl_request(endpoint, method='POST', data=post_data, timeout=5)
        
        if not success:
            return {'in_sync': False, 'error': data}
        
        # Parse sync status from response
        # NSO check-sync returns: {"tailf-ncs:output":{"result":"in-sync"}} or "out-of-sync"
        # Need to check for exact match of "in-sync", not just substring
        import re
        # Look for "result": "in-sync" pattern
        in_sync_match = re.search(r'"result":\s*"in-sync"', data)
        in_sync = bool(in_sync_match)
        
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
