from django.http import JsonResponse
from django.conf import settings


class V1DeprecationMiddleware:
    """
    Middleware to return 410 Gone status for deprecated v1 API endpoints.
    
    This middleware checks if V1_DEPRECATED setting is enabled, and if so,
    returns a 410 status code with a deprecation message for any requests
    to /v1 endpoints.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if v1 deprecation is enabled and path starts with /v1
        if getattr(settings, 'V1_DEPRECATED', False):
            if request.path.startswith('/v1/') or request.path == '/v1':
                return JsonResponse(
                    {
                        'errors': [{
                            'status': '410',
                            'title': 'API Version Deprecated',
                            'detail': 'The v1 API has been deprecated. Please migrate to v2.'
                        }]
                    },
                    status=410
                )
        
        response = self.get_response(request)
        return response
