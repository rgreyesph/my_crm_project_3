# crm_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path('admin513/', admin.site.urls),  # Admin URLs without nested include
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls')),
    path('crm/', include('crm_entities.urls')),
    path('activities/', include('activities.urls')),
    path('pipeline/', include('sales_pipeline.urls')),
    path('users/', include('users.urls')),
    path('health/', lambda request: HttpResponse('OK')),
]