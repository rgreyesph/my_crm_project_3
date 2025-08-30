from django.middleware.security import SecurityMiddleware
from django.http import HttpResponsePermanentRedirect, HttpResponse
import re

class CustomSecurityMiddleware(SecurityMiddleware):
    def process_request(self, request):
        if request.path in ['/health/', '/']:
            return None  # Skip HTTPS redirect
        return super().process_request(request)

class StaticFileBlockingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.blocked_static_patterns = [
            r'\.env$', r'\.git/', r'\.ssh/', r'jenkinsFile$',
            r'\.ini$', r'\.yml$', r'\.yaml$', r'\.vscode/',
            r'js/.*\.chunk\.js$', r'js/main\.[a-f0-9]+\.js$',
            r'config\.json$'
        ]
        self.compiled_patterns = [re.compile(pattern) for pattern in self.blocked_static_patterns]

    def __call__(self, request):
        if request.path.startswith('/static/'):
            path_after_static = request.path[8:]  # Remove '/static/'
            for pattern in self.compiled_patterns:
                if pattern.search(path_after_static):
                    return HttpResponse(status=204)
        return self.get_response(request)