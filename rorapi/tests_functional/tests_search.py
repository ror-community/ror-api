import json
import os
import requests

from django.test import SimpleTestCase


RANK_MAX = 2.404506
R1_MIN = 0.752242
R5_MIN = 0.911979

API_URL = os.environ.get('ROR_BASE_URL', 'http://localhost:8000')


def search(query, url, query_name='query'):
    results = requests.get('{}/organizations'.format(url),
                           {query_name: query}).json()
    if 'items' not in results:
        return []
    return results['items']


def get_rank(affiliation, grid_id, items):
    for i, item in enumerate(items):
        if grid_id == item['external_ids']['GRID']['preferred']:
            return i+1
    return 21


class APIListTestCase(SimpleTestCase):

    def setUp(self):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/dataset_names.json')) as names_file:
            data = json.load(names_file)
        data = [(d, search(d['affiliation'], url=API_URL)) for d in data]
        self.ranks = [get_rank(case['affiliation'], case['grid'], items)
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
