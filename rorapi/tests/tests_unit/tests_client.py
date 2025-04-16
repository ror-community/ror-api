from django.test import TestCase
from rorapi.v2.models.client import Client

class ClientTests(TestCase):
    def test_client_registration(self):
        client = Client.objects.create(email='test@example.com')
        self.assertIsNotNone(client.client_id)

    def test_rate_limiting(self):
        response = self.client.get('/client-id/', HTTP_CLIENT_ID="INVALID_ID")
        self.assertEqual(response.status_code, 429)