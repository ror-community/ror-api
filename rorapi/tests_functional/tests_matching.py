import json
import os
import requests

from django.test import SimpleTestCase


ACCURACY_MIN = 0.337127
PRECISION_MIN = 0.375375
RECALL_MIN = 0.415973

API_URL = os.environ.get('ROR_BASE_URL', 'http://localhost:8000')


def match(affiliation, url):
    results = requests.get('{}/organizations'.format(url),
                           {'query': affiliation}).json()
    if 'items' not in results:
        return []
    if not results['items']:
        return []
    return [results['items'][0]]


def get_grid_ids(items):
    return [item['external_ids']['GRID']['preferred'] for item in items]


class APIListTestCase(SimpleTestCase):

    def setUp(self):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/dataset_affiliations.json')) as affs_file:
            self.results = json.load(affs_file)
        [d.update({'matched_grid_ids': get_grid_ids(match(d['affiliation'],
                                                    url=API_URL))})
         for d in self.results]

    def test_accuracy(self):
        accuracy = \
            len([r for r in self.results
                 if set(r['grid_ids']) == set(r['matched_grid_ids'])]) / \
            len(self.results)
        self.assertTrue(accuracy >= ACCURACY_MIN)

    def test_precision(self):
        precision = \
            sum([len(set(r['grid_ids'])
                     .intersection(set(r['matched_grid_ids'])))
                 for r in self.results]) / \
            sum([len(r['matched_grid_ids']) for r in self.results])
        self.assertTrue(precision >= PRECISION_MIN)

    def test_recall(self):
        recall = \
            sum([len(set(r['grid_ids'])
                     .intersection(set(r['matched_grid_ids'])))
                 for r in self.results]) / \
            sum([len(r['grid_ids']) for r in self.results])
        self.assertTrue(recall >= RECALL_MIN)
