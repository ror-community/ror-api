import json
import os
import re

from .evaluation import search, get_rank, mean_rank, recall_at_n, escape_query
from django.test import SimpleTestCase


RANK_MAX_QUERY = 2.315534
R1_MIN_QUERY = 0.749118
R5_MIN_QUERY = 0.913082

RANK_MAX_QUERY_FUZZY = 2.619402
R1_MIN_QUERY_FUZZY = 0.728343
R5_MIN_QUERY_FUZZY = 0.902090

API_URL = os.environ.get('ROR_BASE_URL', 'http://localhost')


class SearchTestCase(SimpleTestCase):

    def set_up(self, param, rank_max, r1_min, r5_min):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/dataset_names.json')) as names_file:
            data = json.load(names_file)
        data_query = []
        for i, d in enumerate(data):
            data_query.append(
                (d, search(API_URL, param, d['affiliation'])))
            if i % 100 == 0:
                print('Progress: {0:.2f}%'.format(100 * i / len(data)))
        self.ranks = [get_rank(case['ror-id'], items)
                      for case, items in data_query]
        self.rank_max = rank_max
        self.r1_min = r1_min
        self.r5_min = r5_min

    def validate(self, name):
        mean, ci = mean_rank(self.ranks)
        print('\nMean rank for {}: {} {}'.format(name, mean, ci))
        self.assertTrue(mean <= self.rank_max)

        recall_1, ci = recall_at_n(self.ranks, 1)
        print('Recall@1 for {}: {} {}'.format(name, recall_1, ci))
        self.assertTrue(recall_1 >= self.r1_min)

        recall_5, ci = recall_at_n(self.ranks, 5)
        print('Recall@5 for {}: {} {}'.format(name, recall_5, ci))
        self.assertTrue(recall_5 >= self.r5_min)


class QueryFuzzySearchTestCase(SearchTestCase):

    def setUp(self):
        self.param = 'query'
        with open(os.path.join(os.path.dirname(__file__),
                               'data/dataset_names.json')) as names_file:
            data = json.load(names_file)
        data_query = []
        for i, d in enumerate(data):
            data_query.append(
                (d, search(API_URL, 'query',
                           re.sub('([^ ])(?= |$)', r'\g<1>~',
                                  escape_query(d['affiliation'])),
                           escape=False)))
            if i % 100 == 0:
                print('Progress: {0:.2f}%'.format(100 * i / len(data)))
        self.ranks = [get_rank(case['ror-id'], items)
                      for case, items in data_query]
        self.rank_max = RANK_MAX_QUERY_FUZZY
        self.r1_min = R1_MIN_QUERY_FUZZY
        self.r5_min = R5_MIN_QUERY

    def test_search_query(self):
        self.validate('query (fuzzy)')


class QuerySearchTestCase(SearchTestCase):

    def setUp(self):
        self.set_up('query', RANK_MAX_QUERY, R1_MIN_QUERY, R5_MIN_QUERY)

    def test_search_query(self):
        self.validate('query')
