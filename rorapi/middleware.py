from django.core.cache import cache
from django.http import JsonResponse
from rorapi.v2.models import Client
from django.utils.timezone import now
import os

# Toggle Behavior-Based Rate Limiting
ENABLE_BEHAVIORAL_LIMITING = os.getenv("ENABLE_BEHAVIORAL_LIMITING", "False") == "True"

class ClientRateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        client_id = request.headers.get('Client-Id')
        ip_address = request.META.get('REMOTE_ADDR')
        rate_limit = 50  # Default rate limit

        if client_id:
            try:
                client = Client.objects.get(client_id=client_id)
                rate_limit = 2000  # Higher limit for registered users
                
                # Behavior-based throttling (if enabled)
                if ENABLE_BEHAVIORAL_LIMITING:
                    client.request_count += 1
                    client.last_request_at = now()
                    client.save()

                    if client.request_count > 500 and (now() - client.last_request_at).seconds < 300:
                        return JsonResponse({"error": "Rate limit exceeded due to excessive requests"}, status=429)

            except Client.DoesNotExist:
                rate_limit = 50  # Invalid client ID gets the lower limit

        cache_key = f"rate_limit_{client_id or ip_address}"
        request_count = cache.get(cache_key, 0)

        if request_count >= rate_limit:
            return JsonResponse({"error": "Rate limit exceeded"}, status=429)

        cache.set(cache_key, request_count + 1, timeout=300)  # Reset every 5 min
        return self.get_response(request)
