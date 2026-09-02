from django.test import TestCase
from rorapi.v2.models import Client

class ClientTests(TestCase):
    def test_client_registration(self):
        client = Client.objects.create(email='test@example.com')
        self.assertIsNotNone(client.client_id)

    def test_validate_client_id(self):
        response = self.client.get('/validate-client-id/INVALID_ID/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['valid'])
