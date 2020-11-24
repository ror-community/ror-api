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
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/sample.json'), 'r') as f:
                             data = f.read()
                             self.test_data = json.loads(data)
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
                    'country', 'aliases', 'status', 'wikipedia_url', 'labels',
                    'id'
            ]:
                self.assertTrue(l in item)
            self.assertTrue('GRID' in item['external_ids'])
            self.assertTrue('country_code' in item['country'])
            self.assertTrue('country_name' in item['country'])
            self.assertIsNotNone(
                re.match(r'https:\/\/ror\.org\/0\w{6}\d{2}', item['id']))

    def test_compare_data_dump_and_index(self):
        data_index = requests.get(BASE_URL).json()
        #self.assertEquals(data_index['number_of_results'], len(self.data_dump))

        sample = random.sample(self.data_dump, 100)
        for item_dump in sample:
            item_index = requests.get(BASE_URL + '/' + item_dump['id']).json()
            self.maxDiff = None
            attributes = ["id","name","email_address","ip_addresses","established","types","relationships","links","aliases","status","wikipedia_url","labels","country","external_ids"]
            addresses = ["lat","lng","state","city"]
            geonames_city = item_dump['addresses'][0]["geonames_city"]
            # testing in a more granular way
            for a in attributes:
                self.assertEquals(item_index[a],item_dump[a])
            for addr in addresses:
                self.assertEquals(item_index["addresses"][0][addr],item_dump["addresses"][0][addr])
            if geonames_city:
                self.assertEquals(item_index["addresses"][0]["geonames_city"],item_dump["addresses"][0]["geonames_city"])
            elif not(geonames_city):
                # if the geonames_city hashmap is null, making sure the value returned from the index is correspondinly null
                gc = item_index["addresses"][0]["geonames_city"]
                filtered = {k: v for k, v in gc.items() if v is not None}
                gc.clear()
                self.assertIs(bool(gc), False)
