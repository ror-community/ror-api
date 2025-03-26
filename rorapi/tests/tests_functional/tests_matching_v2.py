import json
import os
import re
import requests

from django.test import SimpleTestCase
from statsmodels.stats.api import proportion_confint

ACCURACY_MIN = 0.885741
PRECISION_MIN = 0.915426
RECALL_MIN = 0.920048

#API_URL = os.environ.get('ROR_BASE_URL', 'http://localhost')
#API_URL = 'https://marple.research.crossref.org/match'
API_URL = 'https://api.ror.org'


class AffiliationMatchingTestCase(SimpleTestCase):
    '''
    def match(self, affiliation):
        affiliation = re.sub(r'([\+\-=\&\|><!\(\)\{\}\[\]\^"\~\*\?:\\\/])',
                             lambda m: '\\' + m.group(), affiliation)
        params = {
            'task': 'affiliation-matching',
            'input': affiliation,
            'strategy': 'affiliation-single-search'
        }
        results = requests.get(API_URL, params=params
        ).json()
        return [
            item.get('id') for item in results.get('message').get('items')
            if results.get('message').get('items')
        ]

    '''
    def match(self, affiliation):
        affiliation = re.sub(r'([\+\-=\&\|><!\(\)\{\}\[\]\^"\~\*\?:\\\/])',
                             lambda m: '\\' + m.group(), affiliation)
        results = requests.get('{}/v2/organizations'.format(API_URL), {
            'affiliation': affiliation,
            'single_search': ''
        }).json()
        chosen = [item.get('organization').get('id') for item in results.get('items')
            if item.get('chosen')]
        return chosen


    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/affiliations-crossref-2024-02-19_ror_format.json')) as affs_file:
            self.dataset = json.load(affs_file)
            print(len(self.dataset))
        self.results = []
        for i, d in enumerate(self.dataset):
            self.results.append(self.match(d['affiliation']))
            if i % 100 == 0:
                print('Progress: {0:.2f}%'.format(100 * i / len(self.dataset)))
        with open('resresultsults.json', 'w') as f:
            json.dump([[a, s]
                       for a, s in zip(self.dataset, self.results)], f, indent=2)

    def test_matching(self):
        correct = len([
            d for d, r in zip(self.dataset, self.results)
            if set(d.get('ror_ids')) == set(r)
        ])
        print(correct)
        incorrect = [
            d for d, r in zip(self.dataset, self.results)
            if set(d.get('ror_ids')) != set(r)
        ]
        print(len(incorrect))
        print(incorrect)

        total = len(self.results)
        accuracy = correct / total

        print('Accuracy: {} {}'.format(accuracy,
                                       proportion_confint(correct, total)))
        #self.assertTrue(accuracy >= ACCURACY_MIN)

        correct = sum([
            len(set(r).intersection(set(d.get('ror_ids'))))
            for d, r in zip(self.dataset, self.results)
        ])
        total = sum([len(r) for r in self.results])
        precision = correct / total
        print('Precision: {} {}'.format(precision,
                                        proportion_confint(correct, total)))
        #self.assertTrue(precision >= PRECISION_MIN)

        correct = sum([
            len(set(r).intersection(set(d.get('ror_ids'))))
            for d, r in zip(self.dataset, self.results)
        ])
        total = sum([len(d.get('ror_ids')) for d in self.dataset])
        recall = correct / total
        print('Recall: {} {}'.format(recall,
                                     proportion_confint(correct, total)))
        #self.assertTrue(recall >= RECALL_MIN)
