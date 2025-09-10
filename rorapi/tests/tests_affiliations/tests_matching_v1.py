import json
import os
import re
import time
import requests

from django.test import SimpleTestCase
from statsmodels.stats.api import proportion_confint

ACCURACY_MIN = 0.885741
PRECISION_MIN = 0.915426
RECALL_MIN = 0.920048

API_URL = os.environ.get('ROR_BASE_URL', 'http://localhost')
API_VERSION = 'v1'
TEST_DATASET_SPRINGER = "dataset_affiliations_springer_2023_10_31.json"
TEST_DATASET_CROSSREF = "dataset_affiliations_crossref_2024_02_19.json"


class AffiliationMatchingSpringerTestCase(SimpleTestCase):
    def match(self, affiliation):
        affiliation = re.sub(r'([\+\-=\&\|><!\(\)\{\}\[\]\^"\~\*\?:\\\/])',
                             lambda m: '\\' + m.group(), affiliation)
        results = requests.get('{}/{}/organizations'.format(API_URL, API_VERSION), {
            'affiliation': affiliation
        }).json()
        return [
            item.get('organization').get('id') for item in results.get('items')
            if item.get('chosen')
        ]

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             f'data/{TEST_DATASET_SPRINGER}')) as affs_file:
            self.dataset = json.load(affs_file)
        self.results = []
        for i, d in enumerate(self.dataset):
            time.sleep(0.1)
            self.results.append(self.match(d['affiliation']))
            if i % 100 == 0:
                print('Progress: {0:.2f}%'.format(100 * i / len(self.dataset)))
        with open('results_springer.json', 'w') as f:
            json.dump([[a, s]
                       for a, s in zip(self.dataset, self.results)], f, indent=2)

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

class AffiliationMatchingCrossrefTestCase(SimpleTestCase):
    def match(self, affiliation):
        affiliation = re.sub(r'([\+\-=\&\|><!\(\)\{\}\[\]\^"\~\*\?:\\\/])',
                             lambda m: '\\' + m.group(), affiliation)
        results = requests.get('{}/{}/organizations'.format(API_URL, API_VERSION), {
            'affiliation': affiliation
        }).json()
        return [
            item.get('organization').get('id') for item in results.get('items')
            if item.get('chosen')
        ]

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             f'data/{TEST_DATASET_CROSSREF}')) as affs_file:
            self.dataset = json.load(affs_file)
        self.results = []
        for i, d in enumerate(self.dataset):
            time.sleep(0.1)
            self.results.append(self.match(d['affiliation']))
            if i % 100 == 0:
                print('Progress: {0:.2f}%'.format(100 * i / len(self.dataset)))
        with open('results_crossref.json', 'w') as f:
            json.dump([[a, s]
                       for a, s in zip(self.dataset, self.results)], f, indent=2)

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

