import json
import os
import re
import random
import requests
import zipfile

from django.test import SimpleTestCase
from ..settings import GRID, ROR_DUMP

BASE_URL = '{}/organizations'.format(
    os.environ.get('ROR_BASE_URL', 'http://localhost'))


class DataDumpTestCase(SimpleTestCase):
    def setUp(self):
        with zipfile.ZipFile(ROR_DUMP['ROR_ZIP_PATH'], 'r') as z:
            with z.open('ror.json') as f:
                data = f.read()
                self.data_dump = json.loads(data.decode("utf-8"))

    def test_data_dump(self):
        # sanity check
        self.assertTrue(len(self.data_dump) > 90000)
        # schema check
        for item in self.data_dump:
            for l in [
                    'external_ids', 'links', 'acronyms', 'types', 'name',
                    'country', 'aliases', 'wikipedia_url', 'labels', 'id'
            ]:
                self.assertTrue(l in item)
            self.assertTrue('GRID' in item['external_ids'])
            self.assertTrue('country_code' in item['country'])
            self.assertTrue('country_name' in item['country'])
            self.assertIsNotNone(
                re.match(r'https:\/\/ror\.org\/0\w{6}\d{2}', item['id']))

    def test_compare_data_dump_and_index(self):
        data_index = requests.get(BASE_URL).json()
        self.assertEquals(data_index['number_of_results'], len(self.data_dump))

        sample = random.sample(self.data_dump, 100)
        for item_dump in sample:
            item_index = requests.get(BASE_URL + '/' + item_dump['id']).json()
            self.assertEquals(item_index, item_dump)
