import io
import os
import requests
from django.test import SimpleTestCase
from unittest.mock import patch

BASE_URL = '{}/v2/organizations'.format(
    os.environ.get('ROR_BASE_URL', 'http://localhost')
)

class APIBulkUpdateTestCase(SimpleTestCase):

    def setUp(self):
        os.environ["ROUTE_USER"] = "test_user"
        os.environ["TOKEN"] = "test_token"

    @patch('rorapi.common.views.OurTokenPermission.has_permission', return_value=True)
    def test_bulk_update(self, mock_permission):
        csv_data = """id,name,description
12345,Updated Organization,Updated description.
"""
        csv_file = io.StringIO(csv_data)

        headers = {
            'Token': 'test_token',
            'Route-User': 'test_user'
        }

        response = requests.post(BASE_URL, headers=headers, files={'file': ('bulk_update.csv', csv_file.getvalue())})

        self.assertEqual(response.status_code, 201)
        output = response.json()
        self.assertIn('Successfully processed', output)
