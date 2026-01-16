"""
NSO Client

Handles connections to NSO and device sync checking.
"""

import requests
import logging
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings for NSO connections
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

logger = logging.getLogger(__name__)


class NSOClient:
    """Client for interacting with NSO REST API"""
    
    def __init__(self, host='localhost', port=8888, username=None, password=None):
        """
        Initialize NSO client.
        
        Args:
            host (str): NSO host (default: localhost for tunnel)
            port (int): NSO port
            username (str): NSO username
            password (str): NSO password
        """
        self.base_url = f"https://{host}:{port}"
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # Disable SSL verification
        if username and password:
            self.session.auth = (username, password)
    
    def test_connection(self):
        """
        Test connection to NSO.
        
        Returns:
            dict: Connection status
        """
        try:
            response = self.session.get(
                f"{self.base_url}/restconf/data/tailf-ncs:devices",
                timeout=5
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'message': 'Successfully connected to NSO'
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Authentication failed - check credentials'
                }
            else:
                return {
                    'success': False,
                    'message': f'Connection failed with status {response.status_code}'
                }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Connection refused - check if tunnel is active'
            }
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'Connection timeout'
            }
        except Exception as e:
            logger.exception(f"Error testing connection: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def get_devices(self):
        """
        Get list of devices from NSO.
        
        Returns:
            dict: Device list and status
        """
        try:
            response = self.session.get(
                f"{self.base_url}/restconf/data/tailf-ncs:devices/device",
                headers={'Accept': 'application/yang-data+json'},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                devices = data.get('tailf-ncs:device', [])
                return {
                    'success': True,
                    'devices': devices,
                    'count': len(devices)
                }
            else:
                return {
                    'success': False,
                    'message': f'Failed to get devices: HTTP {response.status_code}'
                }
        except Exception as e:
            logger.exception(f"Error getting devices: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def check_device_sync(self, device_name):
        """
        Check if a specific device is in sync.
        
        Args:
            device_name (str): Name of the device
            
        Returns:
            dict: Sync status
        """
        try:
            response = self.session.post(
                f"{self.base_url}/restconf/data/tailf-ncs:devices/device={device_name}/check-sync",
                headers={'Content-Type': 'application/yang-data+json'},
                json={},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('tailf-ncs:output', {}).get('result', 'unknown')
                return {
                    'success': True,
                    'device': device_name,
                    'sync_result': result,
                    'in_sync': result == 'in-sync'
                }
            else:
                return {
                    'success': False,
                    'device': device_name,
                    'message': f'Failed to check sync: HTTP {response.status_code}'
                }
        except Exception as e:
            logger.exception(f"Error checking sync for {device_name}: {e}")
            return {
                'success': False,
                'device': device_name,
                'message': f'Error: {str(e)}'
            }
    
    def check_all_devices_sync(self):
        """
        Check sync status for all devices.
        
        Returns:
            dict: Sync status for all devices
        """
        devices_result = self.get_devices()
        
        if not devices_result.get('success'):
            return devices_result
        
        devices = devices_result.get('devices', [])
        sync_results = []
        
        for device in devices:
            device_name = device.get('name')
            if device_name:
                sync_status = self.check_device_sync(device_name)
                sync_results.append(sync_status)
        
        in_sync_count = sum(1 for r in sync_results if r.get('in_sync'))
        out_of_sync_count = len(sync_results) - in_sync_count
        
        return {
            'success': True,
            'total_devices': len(sync_results),
            'in_sync': in_sync_count,
            'out_of_sync': out_of_sync_count,
            'results': sync_results
        }
