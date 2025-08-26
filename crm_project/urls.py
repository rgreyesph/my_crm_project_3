# crm_project/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from core.views import block_bots, robots_txt

urlpatterns = [
    
    # Bot blocking patterns - add these BEFORE your other patterns
    re_path(r'^static/js/.*\.chunk\.js$', block_bots),
    re_path(r'^static/js/main\.[a-f0-9]+\.js$', block_bots),
    re_path(r'^static/config\.json$', block_bots),
    re_path(r'^static/\.gitlab-ci\.yml$', block_bots),
    re_path(r'^static/env\.js$', block_bots),
    re_path(r'^static/.*\.(yml|yaml|log|conf|ini|env)$', block_bots),
    
    # Serve robots.txt
    path('robots.txt', robots_txt),
    
    path('admin513/', admin.site.urls),  # Admin URLs without nested include
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('core.urls')),
    path('crm/', include('crm_entities.urls')),
    path('activities/', include('activities.urls')),
    path('pipeline/', include('sales_pipeline.urls')),
    path('users/', include('users.urls')),
    path('health/', lambda request: HttpResponse('OK')),
    
]