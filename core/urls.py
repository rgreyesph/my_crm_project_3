# core/urls.py
from django.urls import path
from .views import DashboardView
from .views import health_check

app_name = 'core' # Optional but good practice

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('', DashboardView.as_view(), name='dashboard'), 
]