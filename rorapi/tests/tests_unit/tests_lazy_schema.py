import importlib
import json
import os
from unittest import mock

from django.test import SimpleTestCase
import requests

from rorapi.common import create_update


VENDORED_SCHEMA_PATH = create_update.VENDORED_SCHEMA_PATH


class LazySchemaTests(SimpleTestCase):
    def setUp(self):
        create_update.get_v2_schema.cache_clear()

    def tearDown(self):
        create_update.get_v2_schema.cache_clear()

    def test_import_does_not_fetch_schema(self):
        with mock.patch(
            "rorapi.common.record_utils.get_file_from_url"
        ) as mock_get:
            importlib.reload(create_update)
            mock_get.assert_not_called()
            self.assertEqual(create_update.get_v2_schema.cache_info().hits, 0)
            self.assertEqual(create_update.get_v2_schema.cache_info().misses, 0)

    def test_loads_schema_from_github_on_first_use(self):
        remote_schema = {"title": "remote", "$id": "remote"}
        with mock.patch.object(
            create_update, "get_file_from_url", return_value=remote_schema
        ) as mock_get:
            schema = create_update.get_v2_schema()
            mock_get.assert_called_once_with(create_update.V2_SCHEMA_URL)
            self.assertEqual(schema, remote_schema)
            # Second call uses the in-process cache.
            self.assertIs(create_update.get_v2_schema(), remote_schema)
            mock_get.assert_called_once()

    def test_falls_back_to_vendored_schema_when_github_fails(self):
        with open(VENDORED_SCHEMA_PATH) as f:
            vendored = json.load(f)
        with mock.patch.object(
            create_update,
            "get_file_from_url",
            side_effect=requests.ConnectionError("github down"),
        ) as mock_get:
            schema = create_update.get_v2_schema()
            mock_get.assert_called_once()
            self.assertEqual(schema, vendored)
            self.assertEqual(schema["$id"], "http://ror.org/schemas/v2.0/organization")

    def test_vendored_schema_file_exists(self):
        self.assertTrue(os.path.isfile(create_update.VENDORED_SCHEMA_PATH))
        with open(create_update.VENDORED_SCHEMA_PATH) as f:
            schema = json.load(f)
        self.assertIn("required", schema)
        self.assertIn("properties", schema)
