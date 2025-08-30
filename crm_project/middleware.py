from django.middleware.security import SecurityMiddleware
from django.http import HttpResponsePermanentRedirect, HttpResponse
import re

class CustomSecurityMiddleware(SecurityMiddleware):
    def process_request(self, request):
        if request.path in ['/health/', '/']:
            return None  # Skip HTTPS redirect
        return super().process_request(request)

class BotBlockingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.blocked_patterns = [
            r'/static/js/.*\.chunk\.js$',
            r'/static/js/main\.[a-f0-9]+\.js$',
            r'/static/config\.json$',
            r'/static/\.env$',
            r'/static/\.git/.*$',
            r'/static/\.ssh/.*$',
            r'/static/\.vscode/.*$',
            r'/static/jenkinsFile$',
            r'/static/.*\.ini$',
            r'/static/.*\.yml$',
            r'/static/.*\.yaml$',
            r'/static/\.[^/]*$',  # Any dotfile
        ]
        self.compiled_patterns = [re.compile(pattern) for pattern in self.blocked_patterns]

    def __call__(self, request):
        # Check if request matches any blocked pattern
        for pattern in self.compiled_patterns:
            if pattern.match(request.path):
                return HttpResponse(status=204)  # No Content
        
        response = self.get_response(request)
        return response