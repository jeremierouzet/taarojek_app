"""
Views for device sync application
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import os

from .ssh_tunnel import tunnel_manager
from .nso_client import NSOClient
from nso_manager.nso_config import get_all_instances, get_nso_instance


@login_required(login_url='/login/')
def index(request):
    """
    Main page - select NSO instance
    """
    instances = get_all_instances()
    active_tunnels = tunnel_manager.get_active_tunnels()
    
    context = {
        'instances': instances,
        'active_tunnels': active_tunnels,
    }
    
    return render(request, 'device_sync/index.html', context)


@login_required(login_url='/login/')
def connect_instance(request, instance_name):
    """
    Connect to an NSO instance (create tunnel)
    """
    instance = get_nso_instance(instance_name)
    
    if not instance:
        return JsonResponse({
            'success': False,
            'message': f'Unknown instance: {instance_name}'
        })
    
    # Get the instance-specific local port
    local_port = instance.get('local_port', 8888)
    
    # Create the tunnel
    result = tunnel_manager.create_tunnel(
        instance_name=instance_name,
        nso_ip=instance['ip'],
        nso_port=instance['port'],
        local_port=local_port,
        ssh_host=instance['ssh_host']
    )
    
    return JsonResponse(result)


@login_required(login_url='/login/')
def disconnect_instance(request, instance_name):
    """
    Disconnect from an NSO instance (close tunnel)
    """
    result = tunnel_manager.close_tunnel(instance_name)
    return JsonResponse(result)


@login_required(login_url='/login/')
def check_sync(request, instance_name):
    """
    Check device sync status for an NSO instance
    """
    # Get instance configuration
    instance = get_nso_instance(instance_name)
    if not instance:
        return JsonResponse({
            'success': False,
            'message': f'Unknown instance: {instance_name}'
        })
    
    # Get the local port for this instance's tunnel
    local_port = tunnel_manager.get_tunnel_port(instance_name)
    if not local_port:
        # Fallback to configured port if tunnel info not available
        local_port = instance.get('local_port', 8888)
    
    # Get NSO credentials from instance configuration (which reads from environment)
    nso_user = instance.get('username')
    nso_pass = instance.get('password')
    
    if not nso_user or not nso_pass:
        return JsonResponse({
            'success': False,
            'message': 'NSO credentials not configured for this instance'
        })
    
    # Create NSO client with the correct port
    client = NSOClient(
        host='localhost',
        port=local_port,
        username=nso_user,
        password=nso_pass
    )
    
    # Test connection first
    conn_test = client.test_connection()
    if not conn_test.get('success'):
        return JsonResponse(conn_test)
    
    # Check all devices sync
    result = client.check_all_devices_sync()
    result['instance'] = instance_name
    
    return JsonResponse(result)


@login_required(login_url='/login/')
def device_sync_view(request, instance_name):
    """
    Device sync status page
    """
    instance = get_nso_instance(instance_name)
    
    if not instance:
        return redirect('index')
    
    active_tunnels = tunnel_manager.get_active_tunnels()
    is_connected = instance_name in active_tunnels
    
    context = {
        'instance_name': instance_name,
        'instance': instance,
        'is_connected': is_connected,
    }
    
    return render(request, 'device_sync/sync_status.html', context)


def login_view(request):
    """
    Login page
    """
    if request.user.is_authenticated:
        return redirect('device_sync:index')
    
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'device_sync:index')
            return redirect(next_url)
        else:
            error = 'Invalid username or password'
    
    return render(request, 'device_sync/login.html', {'error': error})


def logout_view(request):
    """
    Logout user
    """
    logout(request)
    return redirect('device_sync:login')
