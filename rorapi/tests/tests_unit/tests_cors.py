from django.test import TestCase


class CORSClientIdTestCase(TestCase):
    """Test that CORS preflight allows the Client-Id header."""

    def test_preflight_allows_client_id_header(self):
        response = self.client.options(
            '/v2/organizations/02feahw73',
            HTTP_ORIGIN='http://localhost:5173',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET',
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS='Client-Id',
        )
        self.assertIn(response.status_code, (200, 204))
        allow_headers = response.get('Access-Control-Allow-Headers')
        self.assertIsNotNone(allow_headers)
        allowed = [h.strip().lower() for h in allow_headers.split(',')]
        self.assertIn('client-id', allowed)


class AlwaysAllowOriginTestCase(TestCase):
    """Test that Access-Control-Allow-Origin: * is always present."""

    def test_get_without_origin_has_acao_star(self):
        response = self.client.get('/v2/heartbeat')
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')

    def test_get_with_origin_has_acao_star(self):
        response = self.client.get(
            '/v2/heartbeat',
            HTTP_ORIGIN='https://example.org',
        )
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
