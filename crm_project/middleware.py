from django.middleware.security import SecurityMiddleware
from django.http import HttpResponsePermanentRedirect

class CustomSecurityMiddleware(SecurityMiddleware):
    def process_request(self, request):
        if request.path in ['/health/', '/']:
            return None  # Skip HTTPS redirect
        return super().process_request(request)