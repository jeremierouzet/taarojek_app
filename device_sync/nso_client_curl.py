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
    
    def __init__(self, host='localhost', port=8888, username=None, password=None, use_https=True):
        """
        Initialize NSO client.
        
        Args:
            host (str): NSO host
            port (int): NSO port
            username (str): NSO username
            password (str): NSO password
            use_https (bool): Use HTTPS (True) or HTTP (False)
        """
        protocol = 'https' if use_https else 'http'
        self.base_url = f"{protocol}://{host}:{port}"
        self.username = username
        self.password = password
        self.use_https = use_https
    
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
        
        # Add use_https flag (8th parameter)
        cmd.append('false' if not self.use_https else 'true')
        
        try:
            logger.debug(f"Calling wrapper: {wrapper_script} {host}:{port} {endpoint} {method} (https={self.use_https})")
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
                # Provide more helpful error messages
                error_messages = {
                    6: "Could not resolve host",
                    7: "Failed to connect to host",
                    28: "Connection timeout - no data received",
                    35: "SSL/TLS handshake failed - server may be down, rejecting connections, or requires different SSL configuration",
                    52: "Empty reply from server",
                    56: "Connection reset by peer - server actively rejected the connection"
                }
                error_detail = error_messages.get(result.returncode, result.stderr if result.stderr else "No output")
                logger.error(f"Curl failed (rc={result.returncode}): {error_detail} for {endpoint}")
                return False, f"Curl failed (rc={result.returncode}): {error_detail}"
                
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
            # Check for error responses
            elif '<errors' in data or '<error>' in data:
                logger.error(f"NSO returned error: {data[:500]}")
                # Extract error message from XML if possible
                import re
                error_msg_match = re.search(
                    r'<error-message>([^<]+)</error-message>', 
                    data
                )
                if error_msg_match:
                    error_msg = error_msg_match.group(1)
                else:
                    error_msg = data[:200]
                return {
                    'success': False,
                    'message': f'NSO API error: {error_msg}'
                }
            else:
                logger.warning(f"Unexpected response format: {data[:200]}")
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
        # Use /devices container with depth=3 and fields=device(name) to get device list
        # This avoids the "too many instances" error that occurs with /devices/device endpoint
        # The depth parameter limits how deep the XML tree is expanded
        success, data = self._curl_request('/restconf/data/tailf-ncs:devices?depth=3&fields=device(name)', timeout=15)
        
        if not success:
            return {
                'success': False,
                'message': data,
                'devices': []
            }
        
        # Debug: Save a sample of the XML to understand structure
        sample_file = '/tmp/nso_response_sample.xml'
        try:
            with open(sample_file, 'w') as f:
                # Save first 50KB and last 50KB
                f.write("=== FIRST 50KB ===\n")
                f.write(data[:50000])
                f.write("\n\n=== LAST 50KB ===\n")
                f.write(data[-50000:])
            logger.info(f"Saved XML sample to {sample_file}")
        except Exception as e:
            logger.warning(f"Could not save XML sample: {e}")
        
        devices = []
        
        # Parse XML response - extract device names
        import re
        
        # The response contains <device> elements with <name> tags
        # Use regex to find all <device>...</device> blocks and extract names
        device_pattern = re.compile(r'<device[^>]*>(.*?)</device>', re.DOTALL)
        name_pattern = re.compile(r'<name>([^<]+)</name>')
        
        device_matches = device_pattern.findall(data)
        logger.info(f"Found {len(device_matches)} device elements in XML")
        
        for device_xml in device_matches:
            # Extract name from this device block
            name_match = name_pattern.search(device_xml)
            if name_match:
                device_name = name_match.group(1).strip()
                devices.append({'name': device_name})
                logger.debug(f"Found device: {device_name}")
        
        logger.info(f"Parsed {len(devices)} devices from NSO")
        
        # Log first few devices for debugging
        if devices:
            device_names = [d['name'] for d in devices]
            logger.info(f"First few devices: {device_names[:5]}")
        
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
        # NSO check-sync returns: {"tailf-ncs:output":{"result":"in-sync"}} or "out-of-sync" or "locked"
        # Possible statuses: "in-sync", "out-of-sync", "locked"
        # Only "out-of-sync" should be treated as not in sync
        import re
        # Look for "result": "<status>" pattern and extract the status
        result_match = re.search(r'"result":\s*"([^"]+)"', data)
        
        if result_match:
            status = result_match.group(1)
            # Only "out-of-sync" means the device is actually out of sync
            # "in-sync" = in sync
            # "locked" = device is locked (treated as in-sync, not an error)
            # Any other status = assume in sync unless explicitly out-of-sync
            in_sync = (status != "out-of-sync")
        else:
            # If we can't parse the result, default to False (out of sync)
            in_sync = False
        
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
        return self._check_devices_sync(devices)
    
    def check_selected_devices_sync(self, device_names):
        """
        Check sync status for selected devices.
        
        Args:
            device_names (list): List of device names to check
            
        Returns:
            dict: Sync status for selected devices
        """
        if not device_names:
            return {
                'success': False,
                'message': 'No devices selected',
                'stats': {'total': 0, 'in_sync': 0, 'out_of_sync': 0},
                'devices': []
            }
        
        # Create device objects from names
        devices = [{'name': name} for name in device_names]
        return self._check_devices_sync(devices)
    
    def _check_devices_sync(self, devices):
        """
        Internal method to check sync status for a list of devices.
        
        Args:
            devices (list): List of device dictionaries with 'name' key
            
        Returns:
            dict: Sync status results
        """
        # Check sync for each device in parallel using ThreadPoolExecutor
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import time
        
        start_time = time.time()
        device_status = []
        in_sync_count = 0
        out_of_sync_count = 0
        
        def check_device(device):
            """Helper function to check a single device"""
            name = device.get('name')
            sync_status = self.check_device_sync(name)
            is_in_sync = sync_status.get('in_sync', False)
            return {
                'name': name,
                'in_sync': is_in_sync
            }
        
        # Use ThreadPoolExecutor with 10 concurrent workers for parallel checking
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks
            future_to_device = {executor.submit(check_device, device): device for device in devices}
            
            # Collect results as they complete
            for future in as_completed(future_to_device):
                try:
                    result = future.result()
                    device_status.append(result)
                    if result['in_sync']:
                        in_sync_count += 1
                    else:
                        out_of_sync_count += 1
                except Exception as e:
                    device = future_to_device[future]
                    logger.error(f"Error checking device {device.get('name')}: {e}")
                    device_status.append({
                        'name': device.get('name'),
                        'in_sync': False
                    })
                    out_of_sync_count += 1
        
        elapsed = time.time() - start_time
        logger.info(f"Checked {len(devices)} devices in {elapsed:.1f} seconds ({len(devices)/elapsed:.1f} devices/sec)")
        
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
