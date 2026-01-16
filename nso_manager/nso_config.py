"""
NSO Instance Configuration

This module contains configuration for different NSO instances
(Dune and Titan environments: integration, end-to-end, production).
"""

import os
import socket

# Detect if running on dev-vm or local machine
HOSTNAME = socket.gethostname()
ON_DEVM = 'dev-vm' in HOSTNAME.lower()

# Tunnel mode: if on dev-vm, we can access NSO directly (no tunnels needed)
USE_TUNNELS = not ON_DEVM

NSO_INSTANCES = {
    'dune-integration': {
        'name': 'Dune Integration',
        'ip': '138.188.202.5',
        'port': 8888,
        'local_port': 8888,  # Unique local port for tunnel
        'ssh_host': 'devm',
        'use_tunnel': USE_TUNNELS,  # Auto-detect based on hostname
        'description': 'Dune integration environment for testing',
        'color': '#4CAF50',  # Green
        'environment': 'integration',
        'platform': 'dune',
        'username': os.getenv('NSO_USER_INT', 'admin'),
        'password': os.getenv('NSO_PASS_INT', 'admin')
    },
    'titan-integration': {
        'name': 'Titan Integration',
        'ip': '138.188.200.227',
        'port': 8888,
        'local_port': 8889,  # Unique local port for tunnel
        'ssh_host': 'devm',
        'use_tunnel': USE_TUNNELS,  # Auto-detect based on hostname
        'description': 'Titan integration environment for testing',
        'color': '#66BB6A',  # Light Green
        'environment': 'integration',
        'platform': 'titan',
        'username': os.getenv('NSO_USER_INT', 'admin'),
        'password': os.getenv('NSO_PASS_INT', 'admin')
    },
    'dune-e2e': {
        'name': 'Dune End-to-End',
        'ip': '138.188.202.6',
        'port': 8888,
        'local_port': 8890,  # Unique local port for tunnel
        'ssh_host': 'devm',
        'use_tunnel': USE_TUNNELS,  # Auto-detect based on hostname
        'description': 'Dune end-to-end testing environment',
        'color': '#2196F3',  # Blue
        'environment': 'e2e',
        'platform': 'dune',
        'username': os.getenv('NSO_USER_E2E', 'admin'),
        'password': os.getenv('NSO_PASS_E2E', 'admin')
    },
    'titan-e2e': {
        'name': 'Titan End-to-End',
        'ip': '138.188.200.192',
        'port': 8888,
        'local_port': 8891,  # Unique local port for tunnel
        'ssh_host': 'devm',
        'use_tunnel': USE_TUNNELS,  # Auto-detect based on hostname
        'description': 'Titan end-to-end testing environment',
        'color': '#42A5F5',  # Light Blue
        'environment': 'e2e',
        'platform': 'titan',
        'username': os.getenv('NSO_USER_E2E', 'admin'),
        'password': os.getenv('NSO_PASS_E2E', 'admin')
    },
    'titan-production': {
        'name': 'Titan Production',
        'ip': '138.188.195.223',
        'port': 8888,
        'local_port': 8892,  # Unique local port for tunnel
        'ssh_host': 'jump01',  # Production uses jump01 instead of devm
        'use_tunnel': True,  # Always use tunnel via jump01 (even from devm)
        'use_https': False,  # This server uses HTTP, not HTTPS
        'description': 'Titan production environment - use with caution',
        'color': '#F44336',  # Red
        'environment': 'production',
        'platform': 'titan',
        'username': os.getenv('NSO_USER_PROD', 'admin'),
        'password': os.getenv('NSO_PASS_PROD', 'admin')
    },
    # Note: Dune Production not yet available
}

def get_nso_instance(instance_name):
    """
    Get NSO instance configuration by name.
    
    Args:
        instance_name (str): Instance identifier (e.g., 'dune-integration', 'titan-e2e')
        
    Returns:
        dict: Instance configuration or None if not found
    """
    return NSO_INSTANCES.get(instance_name)


def get_all_instances():
    """
    Get all NSO instances.
    
    Returns:
        dict: All NSO instance configurations
    """
    return NSO_INSTANCES


def get_instances_by_environment(environment):
    """
    Get NSO instances filtered by environment.
    
    Args:
        environment (str): Environment name ('integration', 'e2e', 'production')
        
    Returns:
        dict: Filtered NSO instance configurations
    """
    return {
        key: instance for key, instance in NSO_INSTANCES.items()
        if instance.get('environment') == environment
    }


def get_instances_by_platform(platform):
    """
    Get NSO instances filtered by platform.
    
    Args:
        platform (str): Platform name ('dune', 'titan')
        
    Returns:
        dict: Filtered NSO instance configurations
    """
    return {
        key: instance for key, instance in NSO_INSTANCES.items()
        if instance.get('platform') == platform
    }

