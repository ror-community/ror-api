import os
from unittest import mock

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory

from rorapi.common.views import OurTokenPermission

factory = APIRequestFactory()


class OurTokenPermissionTestCase(SimpleTestCase):
    def setUp(self):
        self.permission = OurTokenPermission()

    def test_get_always_allowed(self):
        request = factory.get('/v2/organizations')
        self.assertTrue(self.permission.has_permission(request, None))

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_post_denied_when_env_unset(self):
        request = factory.post(
            '/v2/organizations',
            HTTP_TOKEN='token-value',
            HTTP_ROUTE_USER='route-user',
        )
        self.assertFalse(self.permission.has_permission(request, None))

    @mock.patch.dict(
        os.environ,
        {"TOKEN": "token-value", "ROUTE_USER": "route-user"},
        clear=False,
    )
    def test_post_denied_when_headers_missing(self):
        request = factory.post('/v2/organizations')
        self.assertFalse(self.permission.has_permission(request, None))

    @mock.patch.dict(
        os.environ,
        {"TOKEN": "token-value", "ROUTE_USER": "route-user"},
        clear=False,
    )
    def test_post_denied_when_token_header_missing(self):
        request = factory.post(
            '/v2/organizations',
            HTTP_ROUTE_USER='route-user',
        )
        self.assertFalse(self.permission.has_permission(request, None))

    @mock.patch.dict(
        os.environ,
        {"TOKEN": "token-value", "ROUTE_USER": "route-user"},
        clear=False,
    )
    def test_post_denied_when_route_user_header_missing(self):
        request = factory.post(
            '/v2/organizations',
            HTTP_TOKEN='token-value',
        )
        self.assertFalse(self.permission.has_permission(request, None))

    @mock.patch.dict(
        os.environ,
        {"TOKEN": "token-value", "ROUTE_USER": "route-user"},
        clear=False,
    )
    def test_post_denied_on_mismatch(self):
        request = factory.post(
            '/v2/organizations',
            HTTP_TOKEN='wrong-token',
            HTTP_ROUTE_USER='route-user',
        )
        self.assertFalse(self.permission.has_permission(request, None))

        request = factory.post(
            '/v2/organizations',
            HTTP_TOKEN='token-value',
            HTTP_ROUTE_USER='wrong-user',
        )
        self.assertFalse(self.permission.has_permission(request, None))

    @mock.patch.dict(
        os.environ,
        {"TOKEN": "token-value", "ROUTE_USER": "route-user"},
        clear=False,
    )
    def test_post_allowed_on_match(self):
        request = factory.post(
            '/v2/organizations',
            HTTP_TOKEN='token-value',
            HTTP_ROUTE_USER='route-user',
        )
        self.assertTrue(self.permission.has_permission(request, None))

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_post_denied_when_env_and_headers_both_missing(self):
        """Regression: None == None previously granted write access."""
        request = factory.post('/v2/organizations')
        self.assertFalse(self.permission.has_permission(request, None))
