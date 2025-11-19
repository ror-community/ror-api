from django.test import TestCase, RequestFactory, override_settings
from django.http import JsonResponse
from rorapi.middleware.deprecation import V1DeprecationMiddleware
import json


class V1DeprecationMiddlewareTestCase(TestCase):
    """
    Tests for V1DeprecationMiddleware that returns 410 Gone for deprecated v1 endpoints.
    """

    def setUp(self):
        self.factory = RequestFactory()
        
        # Mock get_response function
        def get_response(request):
            return JsonResponse({'message': 'success'}, status=200)
        
        self.get_response = get_response
        self.middleware = V1DeprecationMiddleware(self.get_response)

    @override_settings(V1_DEPRECATED=True)
    def test_v1_path_returns_410_when_deprecated(self):
        """Test that /v1/ paths return 410 when V1_DEPRECATED is True"""
        request = self.factory.get('/v1/organizations')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 410)
        content = json.loads(response.content.decode('utf-8'))
        self.assertIn('errors', content)
        self.assertEqual(content['errors'][0]['status'], '410')
        self.assertEqual(content['errors'][0]['title'], 'API Version Deprecated')

    @override_settings(V1_DEPRECATED=True)
    def test_v1_exact_path_returns_410_when_deprecated(self):
        """Test that exact /v1 path returns 410 when V1_DEPRECATED is True"""
        request = self.factory.get('/v1')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 410)
        content = json.loads(response.content.decode('utf-8'))
        self.assertIn('errors', content)

    @override_settings(V1_DEPRECATED=True)
    def test_v2_path_passes_through_when_v1_deprecated(self):
        """Test that /v2/ paths work normally even when V1_DEPRECATED is True"""
        request = self.factory.get('/v2/organizations')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['message'], 'success')

    @override_settings(V1_DEPRECATED=False)
    def test_v1_path_passes_through_when_not_deprecated(self):
        """Test that /v1/ paths work normally when V1_DEPRECATED is False"""
        request = self.factory.get('/v1/organizations')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['message'], 'success')

    @override_settings(V1_DEPRECATED=False)
    def test_v2_path_passes_through_when_v1_not_deprecated(self):
        """Test that /v2/ paths work normally when V1_DEPRECATED is False"""
        request = self.factory.get('/v2/organizations')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['message'], 'success')

    @override_settings(V1_DEPRECATED=None)
    def test_v1_path_passes_through_when_setting_not_set(self):
        """Test that /v1/ paths work when V1_DEPRECATED setting doesn't exist"""
        # Don't use override_settings, rely on default behavior
        request = self.factory.get('/v1/organizations')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(content['message'], 'success')

    @override_settings(V1_DEPRECATED=True)
    def test_root_path_passes_through(self):
        """Test that root path is not affected by middleware"""
        request = self.factory.get('/')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)

    @override_settings(V1_DEPRECATED=True)
    def test_other_paths_pass_through(self):
        """Test that non-v1 paths pass through normally"""
        request = self.factory.get('/heartbeat')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)

    @override_settings(V1_DEPRECATED=True)
    def test_v1_with_query_params_returns_410(self):
        """Test that /v1/ paths with query parameters return 410"""
        request = self.factory.get('/v1/organizations?query=test')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 410)

    @override_settings(V1_DEPRECATED=True)
    def test_v1_post_request_returns_410(self):
        """Test that POST requests to /v1/ paths return 410"""
        request = self.factory.post('/v1/organizations')
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 410)

    @override_settings(V1_DEPRECATED=True)
    def test_deprecation_error_message_format(self):
        """Test that the deprecation error message follows the expected format"""
        request = self.factory.get('/v1/organizations')
        response = self.middleware(request)
        
        content = json.loads(response.content.decode('utf-8'))
        self.assertIn('errors', content)
        self.assertEqual(len(content['errors']), 1)
        
        error = content['errors'][0]
        self.assertIn('status', error)
        self.assertIn('title', error)
        self.assertIn('detail', error)
        self.assertIn('migrate to v2', error['detail'])
