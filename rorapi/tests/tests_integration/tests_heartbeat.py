from django.test import SimpleTestCase


class HeartbeatViewTestCase(SimpleTestCase):
    """Needs a live organizations-v2 index, so it runs with the integration suite."""

    def test_heartbeat_success(self):
        response = self.client.get('/heartbeat')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'OK')
