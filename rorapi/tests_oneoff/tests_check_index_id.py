import itertools
import json
import os
import re
import requests
import random
import zipfile
from django.test import SimpleTestCase
from ..settings import BASE_DIR, ROR_DUMP, ES_VARS

BASE_URL = '{}/organizations'.format(
    os.environ.get('ROR_BASE_URL', 'http://localhost'))
PREVIOUS_INDEX = "2021-04-06"
# this is currently only looking at active records
# the data dump is presumed to only have active records
# as is the index
# this will change soon
# this is assuming that the data to be tested is indexed
# this is done for a sanity check in case the schema changes and we want to index the same IDs that are there but with new metadata. Therefore the id needs to be the same as the previously correct data
class CheckIndexID(SimpleTestCase):
    def setUp(self):
        ROR_DUMP['DIR'] = os.path.join(BASE_DIR, 'rorapi', 'data','ror-{}'.format(PREVIOUS_INDEX))
        ROR_DUMP['ROR_ZIP_PATH'] = os.path.join(ROR_DUMP['DIR'], 'ror.zip')
        with zipfile.ZipFile(ROR_DUMP['ROR_ZIP_PATH'], 'r') as z:
            with z.open('ror.json') as f:
                data = f.read()
                self.previous_data = json.loads(data.decode("utf-8"))

    def test_compare_previous_data_and_index(self):
        data_index = requests.get(BASE_URL).json()
        self.assertEquals(data_index['number_of_results'], len(self.previous_data))

        for record in self.previous_data:
            query = requests.get(BASE_URL + '/' + record['id'])
            current_record = query.json()
            file_grid_id = record['external_ids']['GRID']['all']
            indexed_grid_id = current_record['external_ids']['GRID']['all']
            # if there are errors, this should fail as false and print out the error
            self.assertTrue(bool(current_record.get('id')),current_record)
            self.assertEqual(file_grid_id,indexed_grid_id,f"For file {record['id']} and indexed {current_record['id']}, file grid id: {file_grid_id} is not equal to indexed grid id: {indexed_grid_id}")
            self.assertEqual(record['name'],current_record['name'], f"{record['id']} is not the same as {current_record['id']}")
