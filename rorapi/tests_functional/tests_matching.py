import json
import os
import re
import requests

from django.test import SimpleTestCase


ACCURACY_MIN = 0.337127
PRECISION_MIN = 0.375375
RECALL_MIN = 0.415973

API_URL = os.environ.get('ROR_BASE_URL', 'http://localhost')


class AffiliationMatchingTestCase(SimpleTestCase):

    def match(self, affiliation):
        affiliation = re.sub(r'([\+\-=\&\|><!\(\)\{\}\[\]\^"\~\*\?:\\\/])',
                             lambda m: '\\' + m.group(), affiliation)
        results = requests.get('{}/organizations'.format(API_URL),
                               {'query': affiliation}).json()
        if 'items' not in results:
            return []
        if not results['items']:
            return []
        return [results['items'][0]]

    def get_grid_ids(self, items):
        return [item['external_ids']['GRID']['preferred'] for item in items]

    def setUp(self):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/dataset_affiliations.json')) as affs_file:
            self.results = json.load(affs_file)
        [d.update({'matched': self.get_grid_ids(self.match(d['affiliation']))})
         for d in self.results]

    def test_accuracy(self):
        accuracy = \
            len([r for r in self.results
                 if set(r['grid_ids']) == set(r['matched'])]) / \
            len(self.results)
        self.assertTrue(accuracy >= ACCURACY_MIN)

    def test_precision(self):
        precision = \
            sum([len(set(r['grid_ids'])
                     .intersection(set(r['matched'])))
                 for r in self.results]) / \
            sum([len(r['matched']) for r in self.results])
        self.assertTrue(precision >= PRECISION_MIN)

    def test_recall(self):
        recall = \
            sum([len(set(r['grid_ids'])
                     .intersection(set(r['matched'])))
                 for r in self.results]) / \
            sum([len(r['grid_ids']) for r in self.results])
        self.assertTrue(recall >= RECALL_MIN)
