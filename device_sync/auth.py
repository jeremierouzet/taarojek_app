"""
Authentication middleware for NSO Manager
"""

from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.urls import reverse
from functools import wraps


def login_required_basic(view_func):
    """
    Decorator for views that checks that the user is logged in.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('device_sync:login')
        return view_func(request, *args, **kwargs)
    return wrapper
