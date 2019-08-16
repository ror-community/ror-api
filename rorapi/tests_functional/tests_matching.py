import json
import os
import re
import requests

from django.test import SimpleTestCase
from statsmodels.stats.api import proportion_confint

ACCURACY_MIN = 0.885741
PRECISION_MIN = 0.915426
RECALL_MIN = 0.920048

API_URL = os.environ.get('ROR_BASE_URL', 'http://localhost')


class AffiliationMatchingTestCase(SimpleTestCase):
    def match(self, affiliation):
        affiliation = re.sub(r'([\+\-=\&\|><!\(\)\{\}\[\]\^"\~\*\?:\\\/])',
                             lambda m: '\\' + m.group(), affiliation)
        results = requests.get('{}/organizations'.format(API_URL), {
            'affiliation': affiliation
        }).json()
        return [
            item.get('organization').get('id') for item in results.get('items')
            if item.get('chosen')
        ]

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/dataset_affiliations.json')) as affs_file:
            self.dataset = json.load(affs_file)
        self.results = [self.match(d['affiliation']) for d in self.dataset]

    def test_matching(self):
        correct = len([
            d for d, r in zip(self.dataset, self.results)
            if set(d.get('ror_ids')) == set(r)
        ])
        total = len(self.results)
        accuracy = correct / total

        print('Accuracy: {} {}'.format(accuracy,
                                       proportion_confint(correct, total)))
        self.assertTrue(accuracy >= ACCURACY_MIN)

        correct = sum([
            len(set(r).intersection(set(d.get('ror_ids'))))
            for d, r in zip(self.dataset, self.results)
        ])
        total = sum([len(r) for r in self.results])
        precision = correct / total
        print('Precision: {} {}'.format(precision,
                                        proportion_confint(correct, total)))
        self.assertTrue(precision >= PRECISION_MIN)

        correct = sum([
            len(set(r).intersection(set(d.get('ror_ids'))))
            for d, r in zip(self.dataset, self.results)
        ])
        total = sum([len(d.get('ror_ids')) for d in self.dataset])
        recall = correct / total
        print('Recall: {} {}'.format(recall,
                                     proportion_confint(correct, total)))
        self.assertTrue(recall >= RECALL_MIN)
