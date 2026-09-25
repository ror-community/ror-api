from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.exceptions import Throttled
from rest_framework.test import APIRequestFactory

from rorapi.common.views import ClientRegistrationThrottle, ClientRegistrationView

factory = APIRequestFactory()


class ClientRegistrationThrottleTests(SimpleTestCase):
    def setUp(self):
        # DRF SimpleRateThrottle binds django.core.cache.cache at import time.
        ClientRegistrationThrottle.cache = cache
        cache.clear()
        self.view = ClientRegistrationView()

    def test_view_uses_class_rate_throttle(self):
        self.assertEqual(ClientRegistrationThrottle.rate, "5/hour")
        self.assertEqual(
            ClientRegistrationView.throttle_classes, [ClientRegistrationThrottle]
        )

    def test_allows_five_anonymous_requests_then_throttles(self):
        request = self.view.initialize_request(factory.post("/v2/register"))
        for _ in range(5):
            self.view.check_throttles(request)
        with self.assertRaises(Throttled):
            self.view.check_throttles(request)
