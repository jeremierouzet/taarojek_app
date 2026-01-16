"""
URL Configuration for device_sync app
"""

from django.urls import path
from . import views

app_name = 'device_sync'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('connect/<str:instance_name>/', views.connect_instance, name='connect'),
    path('disconnect/<str:instance_name>/', views.disconnect_instance, name='disconnect'),
    path('sync/<str:instance_name>/', views.device_sync_view, name='sync_view'),
    path('api/check-sync/<str:instance_name>/', views.check_sync, name='check_sync'),
]
