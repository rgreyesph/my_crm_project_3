# activities/urls.py
from django.urls import path
from . import views # Import views from current directory
from .views import task_export_view, call_export_view, meeting_export_view


app_name = 'activities'

urlpatterns = [
    # Task URLs
    path('tasks/', views.TaskListView.as_view(), name='task-list'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task-create'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/update/', views.TaskUpdateView.as_view(), name='task-update'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task-delete'),
    path('tasks/export/', task_export_view, name='task-export'), # Added


    # Call URLs
    path('calls/', views.CallListView.as_view(), name='call-list'),
    path('calls/create/', views.CallCreateView.as_view(), name='call-create'),
    path('calls/<int:pk>/', views.CallDetailView.as_view(), name='call-detail'),
    path('calls/<int:pk>/update/', views.CallUpdateView.as_view(), name='call-update'),
    path('calls/<int:pk>/delete/', views.CallDeleteView.as_view(), name='call-delete'),
    path('calls/export/', call_export_view, name='call-export'), # Added


    # Meeting URLs
    path('meetings/', views.MeetingListView.as_view(), name='meeting-list'),
    path('meetings/create/', views.MeetingCreateView.as_view(), name='meeting-create'),
    path('meetings/<int:pk>/', views.MeetingDetailView.as_view(), name='meeting-detail'),
    path('meetings/<int:pk>/update/', views.MeetingUpdateView.as_view(), name='meeting-update'),
    path('meetings/<int:pk>/delete/', views.MeetingDeleteView.as_view(), name='meeting-delete'),
    path('meetings/export/', meeting_export_view, name='meeting-export'), # Added

]