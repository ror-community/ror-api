from django.test import TestCase
from rorapi.v2.models import Client

class ClientTests(TestCase):
    def test_client_registration(self):
        client = Client.objects.create(email='test@example.com')
        self.assertIsNotNone(client.client_id)