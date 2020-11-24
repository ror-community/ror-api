import itertools
import json
import os
import re
import requests

from django.test import SimpleTestCase
from ..settings import ROR_API, ES_VARS

BASE_URL = '{}/organizations'.format(
    os.environ.get('ROR_BASE_URL', 'http://localhost'))


class APITestCase(SimpleTestCase):
    def get_total(self, output):
        return output['number_of_results']

    def get_total_from_query(self, query):
        return self.get_total(requests.get(BASE_URL, query).json())

    def verify_full_list(self, output):
        # TODO use JSON schema instead?
        for k in ['number_of_results', 'time_taken', 'items', 'meta']:
            self.assertTrue(k in output)

        self.assertEquals(len(output['items']), 20)
        for i in output['items']:
            for k in ['id', 'name']:
                self.assertTrue(k in i)
                self.assertIsNotNone(
                    re.match(r'https:\/\/ror\.org\/0\w{6}\d{2}', i['id']))

        self.assertTrue('types' in output['meta'])
        self.assertTrue(len(output['meta']['types']) > 0)
        for t in output['meta']['types']:
            self.assertTrue('id' in t)
            self.assertTrue('count' in t)

        self.assertTrue('countries' in output['meta'])
        self.assertTrue(len(output['meta']['countries']) > 0)
        for t in output['meta']['countries']:
            self.assertTrue('id' in t)
            self.assertTrue('count' in t)

    def verify_empty(self, output):
        self.assertEquals(self.get_total(output), 0)
        self.assertEquals(output['items'], [])
        self.assertEquals(output['meta'], {'types': [], 'countries': []})

    def verify_single_item(self, output, org):
        self.assertEquals(self.get_total(output), 1)
        self.assertEquals(output['items'][0], org)

    def test_list_organizations(self):
        output = requests.get(BASE_URL).json()

        self.verify_full_list(output)
        # sanity check
        self.assertTrue(self.get_total(output) > 50000)

    def test_query_organizations(self):
        total = self.get_total_from_query({})

        output = requests.get(BASE_URL, {'query': 'university'}).json()
        self.verify_full_list(output)
        self.assertTrue(self.get_total(output) < total)

    def test_deprecated_queries(self):
        for q in [{}, {
                'page': 7
        }, {
                'filter': 'country.country_code:US'
        }, {
                'filter': 'country.country_code:US',
                'page': 3
        }]:
            status_code = requests.get(BASE_URL, dict(q, query='university')).status_code
            if status_code != 200:
                print("failing query: ", dict(q, query='university'))
            output = requests.get(BASE_URL, dict(q, query='university')).json()
            del output['time_taken']
            output_deprecated = requests.get(
                BASE_URL, dict(q, **{'query.name': 'university'})).json()
            del output_deprecated['time_taken']
            self.assertEqual(output_deprecated, output)


    def verify_paging(self, query):
        total = self.get_total_from_query(query)
        max_page = min(400, int(total / ROR_API['PAGE_SIZE']))
        outputs = [
            requests.get(BASE_URL, dict(query, page=n)).json()
            for n in range(1, max_page + 1)
        ]

        for output in outputs:
            self.verify_full_list(output)
        # all responses declare the same number of results
        self.assertEquals(len(set([self.get_total(o) for o in outputs])), 1)
        # IDs of the items listed are all distinct
        self.assertEquals(len(set([o['items'][0]['id'] for o in outputs])),
                          max_page)
        # all responses have the same aggregations
        self.assertEquals(len(set([json.dumps(o['meta']) for o in outputs])),
                          1)

    def test_paging(self):
        self.verify_paging({})

        self.verify_paging({'query': 'university'})
        self.verify_paging({
            'query': 'university',
            'filter': 'types:Healthcare'
        })

    def test_iteration(self):
        total = 10000
        ids = []
        for page in range(1, ES_VARS['MAX_PAGE'] + 1):
            request = requests.get(BASE_URL, {'page': page})
            if request.status_code != 200:
                print("failing query: ", {'page': page})
            output = requests.get(BASE_URL, {'page': page}).json()
            ids.extend([i['id'] for i in output['items']])
        self.assertEquals(len(ids), total)
        self.assertEquals(len(set(ids)), total)

    def verify_filtering(self, query):
        aggregations = requests.get(BASE_URL, query).json()['meta']
        t_aggrs = aggregations['types']
        c_aggrs = aggregations['countries']

        for t_aggr in t_aggrs:
            filter_string = 'types:{}'.format(t_aggr['title'])
            params = dict(query, filter=filter_string)
            output = requests.get(BASE_URL, params).json()

            self.assertEquals(self.get_total(output), t_aggr['count'])
            for i in output['items']:
                self.assertTrue(t_aggr['title'] in i['types'])
            self.assertTrue(any([t_aggr == t
                                 for t in output['meta']['types']]))

        for c_aggr in c_aggrs:
            filter_string = 'country.country_code:{}' \
                .format(c_aggr['id'].upper())
            params = dict(query, filter=filter_string)
            output = requests.get(BASE_URL, params).json()

            self.assertEquals(self.get_total(output), c_aggr['count'])
            for i in output['items']:
                self.assertEquals(c_aggr['id'].upper(),
                                  i['country']['country_code'])
            self.assertTrue(
                any([c_aggr == c for c in output['meta']['countries']]))

        for t_aggr, c_aggr in itertools.product(t_aggrs, c_aggrs):
            filter_string = 'country.country_code:{},types:{}' \
                .format(c_aggr['id'].upper(), t_aggr['title'])
            params = dict(query, filter=filter_string)
            status_code = requests.get(BASE_URL, params).status_code
            if status_code != 200:
                print("failing params: ", params)
            output = requests.get(BASE_URL, params).json()
            if self.get_total(output) == 0:
                self.verify_empty(output)
                continue
            self.assertTrue(self.get_total(output) <= t_aggr['count'])
            self.assertTrue(self.get_total(output) <= c_aggr['count'])
            for i in output['items']:
                self.assertTrue(t_aggr['title'] in i['types'])
                self.assertEquals(c_aggr['id'].upper(),
                                  i['country']['country_code'])
            self.assertTrue(
                any([t_aggr['id'] == t['id']
                     for t in output['meta']['types']]))
            self.assertTrue(
                any([
                    c_aggr['id'] == c['id']
                    for c in output['meta']['countries']
                ]))

    def test_filtering(self):
        self.verify_filtering({})
        self.verify_filtering({'query': 'university'})

    def test_empty_output(self):
        output = requests.get(BASE_URL, {'filter': 'types:notatype'}).json()
        self.verify_empty(output)

    def test_query_retrieval(self):
        for test_org in requests.get(BASE_URL).json()['items']:
            for test_id in \
                [test_org['id'],
                 re.sub('https', 'http', test_org['id']),
                 re.sub(r'https:\/\/', '', test_org['id']),
                 re.sub(r'https:\/\/ror.org\/', '', test_org['id']),
                 re.sub(r'https:\/\/ror.org\/', r'ror.org%2F', test_org['id']),
                 re.sub(r'https:\/\/ror.org\/', r'http%3A%2F%2Fror.org%2F',
                        test_org['id']),
                 re.sub(r'https:\/\/ror.org\/', r'https%3A%2F%2Fror.org%2F',
                        test_org['id'])]:
                output = requests.get(BASE_URL, {'query': test_id}).json()
                self.verify_single_item(output, test_org)

    def test_retrieval(self):
        for test_org in requests.get(BASE_URL).json()['items']:
            for test_id in \
                [test_org['id'],
                 re.sub('https', 'http', test_org['id']),
                 re.sub(r'https:\/\/', '', test_org['id']),
                 re.sub(r'https:\/\/ror.org\/', '', test_org['id']),
                 re.sub(r'https:\/\/ror.org\/', r'ror.org%2F', test_org['id']),
                 re.sub(r'https:\/\/ror.org\/', r'http%3A%2F%2Fror.org%2F',
                        test_org['id']),
                 re.sub(r'https:\/\/ror.org\/', r'https%3A%2F%2Fror.org%2F',
                        test_org['id'])]:
                output = requests.get(BASE_URL + '/' + test_id).json()
                self.assertEquals(output, test_org)

    def test_query_grid_retrieval(self):
        for test_org in requests.get(BASE_URL).json()['items']:
            grid = test_org['external_ids']['GRID']['preferred']
            output = requests.get(BASE_URL, {'query': '"' + grid + '"'}).json()
            self.verify_single_item(output, test_org)

    def test_error(self):
        output = requests.get(BASE_URL, {
            'query': 'query',
            'illegal': 'whatever',
            'another': 3
        }).json()
        self.assertEquals(len(output['errors']), 2)
        self.assertTrue(any(['\'illegal\'' in e for e in output['errors']]))
        self.assertTrue(any(['\'another\'' in e for e in output['errors']]))

        output = requests.get(BASE_URL, {
            'query': 'query',
            'filter': 'fi1:e,types:F,f3,field2:44'
        }).json()
        self.assertEquals(len(output['errors']), 3)
        self.assertTrue(any(['\'fi1\'' in e for e in output['errors']]))
        self.assertTrue(any(['\'field2\'' in e for e in output['errors']]))
        self.assertTrue(any(['\'f3\'' in e for e in output['errors']]))

        output = requests.get(BASE_URL, {
            'query': 'query',
            'page': 'whatever'
        }).json()
        self.assertEquals(len(output['errors']), 1)
        self.assertTrue('\'whatever\'' in output['errors'][0])

        output = requests.get(BASE_URL, {
            'query': 'query',
            'page': '10000'
        }).json()
        self.assertEquals(len(output['errors']), 1)
        self.assertTrue('\'10000\'' in output['errors'][0])

        output = requests.get(
            BASE_URL, {
                'query': 'query',
                'illegal': 'whatever',
                'filter': 'fi1:e,types:F,f3,field2:44',
                'another': 3,
                'page': 'third'
            }).json()
        self.assertEquals(len(output['errors']), 6)
        self.assertTrue(any(['\'illegal\'' in e for e in output['errors']]))
        self.assertTrue(any(['\'another\'' in e for e in output['errors']]))
        self.assertTrue(any(['\'fi1\'' in e for e in output['errors']]))
        self.assertTrue(any(['\'field2\'' in e for e in output['errors']]))
        self.assertTrue(any(['\'f3\'' in e for e in output['errors']]))
        self.assertTrue(any(['\'third\'' in e for e in output['errors']]))

        output = requests.get(BASE_URL + '/https://ror.org/0qwerty89').json()
        self.assertEquals(len(output['errors']), 1)
        self.assertTrue('\'https://ror.org/0qwerty89\'' in output['errors'][0])
