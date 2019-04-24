import json
import os
import requests

from django.test import SimpleTestCase


RANK_MAX = 2.404506
R1_MIN = 0.752242
R5_MIN = 0.911979

API_URL = os.environ.get('ROR_BASE_URL', 'http://localhost:8000')


class SearchTestCase(SimpleTestCase):

    def search(self, query):
        results = requests.get('{}/organizations'.format(API_URL),
                               {'query': query}).json()
        if 'items' not in results:
            return []
        return results['items']

    def get_rank(self, grid_id, items):
        for i, item in enumerate(items):
            if grid_id == item['external_ids']['GRID']['preferred']:
                return i+1
        return 21

    def setUp(self):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/dataset_names.json')) as names_file:
            data = json.load(names_file)
        data = [(d, self.search(d['affiliation'])) for d in data]
        self.ranks = [self.get_rank(case['grid'], items)
                      for case, items in data]

    def test_rank(self):
        mean_rank = sum(self.ranks) / len(self.ranks)
        self.assertTrue(mean_rank <= RANK_MAX)

    def test_recall_1(self):
        recall_1 = \
            sum([1 if r == 1 else 0 for r in self.ranks]) / len(self.ranks)
        self.assertTrue(recall_1 >= R1_MIN)

    def test_recall_5(self):
        recall_5 = \
            sum([1 if r <= 5 else 0 for r in self.ranks]) / len(self.ranks)
        self.assertTrue(recall_5 >= R5_MIN)
