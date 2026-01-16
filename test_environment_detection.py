#!/usr/bin/env python3
"""
Test script to verify environment detection and tunnel configuration

This script tests:
1. Hostname detection (devm vs local)
2. Tunnel creation logic (enabled on local, disabled on devm)
3. SSH host configuration (jump01 for production, devm for others)
"""

import socket
from nso_manager.nso_config import ON_DEVM, USE_TUNNELS, get_nso_instance

def test_environment_detection():
    """Test environment detection"""
    hostname = socket.gethostname()
    print(f"🖥️  Current hostname: {hostname}")
    print(f"📍 Detected as devm: {ON_DEVM}")
    print(f"🔌 Tunnels enabled: {USE_TUNNELS}")
    print()
    
    if ON_DEVM:
        print("✅ Running on dev-vm")
        print("   → Direct access to NSO instances (no SSH tunnels)")
        print("   → Using actual NSO IP addresses")
    else:
        print("✅ Running on local machine")
        print("   → SSH tunnels required")
        print("   → Connecting via jump hosts (devm or jump01)")
    print()

def test_instance_configuration():
    """Test instance configurations"""
    instances = [
        'titan-integration',
        'titan-e2e', 
        'titan-production',
        'dune-integration',
        'dune-e2e'
    ]
    
    print("📋 Instance Configurations:")
    print("-" * 80)
    
    for instance_name in instances:
        instance = get_nso_instance(instance_name)
        if instance:
            print(f"\n{instance['name']}:")
            print(f"  IP: {instance['ip']}:{instance['port']}")
            print(f"  SSH Host: {instance['ssh_host']}")
            print(f"  Local Port: {instance.get('local_port', 'N/A')}")
            print(f"  Use Tunnel: {instance.get('use_tunnel', True)}")
            print(f"  Use HTTPS: {instance.get('use_https', True)}")
            
            # Special notes
            if instance_name == 'titan-production':
                print(f"  ⚠️  Requires MFA: Run 'ssh -fN jump01' first (ControlMaster)")
                print(f"  ⚠️  Uses HTTP (not HTTPS)")
                print(f"  ⚠️  SSH Port 443 for jump01")

def main():
    print("=" * 80)
    print("🧪 Environment Detection Test")
    print("=" * 80)
    print()
    
    test_environment_detection()
    test_instance_configuration()
    
    print("\n" + "=" * 80)
    print("✅ Test completed")
    print("=" * 80)

if __name__ == "__main__":
    main()
