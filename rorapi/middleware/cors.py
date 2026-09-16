class AlwaysAllowOriginMiddleware:
    """Always set Access-Control-Allow-Origin: * on responses.

    django-cors-headers only adds this header when the request has an Origin
    header. Edge caches that ignore Vary: Origin can then serve a no-Origin
    response to browsers without ACAO. Setting * unconditionally makes those
    cached responses safe for browsers (credentialed CORS is not used).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Access-Control-Allow-Origin'] = '*'
        return response
