import importlib
import json
import os

from django.test import SimpleTestCase

from rorapi.common import create_update


class LazySchemaTests(SimpleTestCase):
    def setUp(self):
        create_update.get_v2_schema.cache_clear()

    def tearDown(self):
        create_update.get_v2_schema.cache_clear()

    def test_import_does_not_load_schema(self):
        importlib.reload(create_update)
        self.assertEqual(create_update.get_v2_schema.cache_info().hits, 0)
        self.assertEqual(create_update.get_v2_schema.cache_info().misses, 0)

    def test_loads_vendored_schema_on_first_use(self):
        with open(create_update.VENDORED_SCHEMA_PATH) as f:
            expected = json.load(f)
        schema = create_update.get_v2_schema()
        self.assertEqual(schema, expected)
        self.assertEqual(schema["$id"], "http://ror.org/schemas/v2.0/organization")
        # Second call uses the in-process cache (same object).
        self.assertIs(create_update.get_v2_schema(), schema)
        info = create_update.get_v2_schema.cache_info()
        self.assertEqual(info.hits, 1)
        self.assertEqual(info.misses, 1)

    def test_vendored_schema_file_exists(self):
        self.assertTrue(os.path.isfile(create_update.VENDORED_SCHEMA_PATH))
        with open(create_update.VENDORED_SCHEMA_PATH) as f:
            schema = json.load(f)
        self.assertIn("required", schema)
        self.assertIn("properties", schema)
