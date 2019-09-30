import json
import mock
import os

from django.test import SimpleTestCase
from ..queries import get_ror_id, validate, build_search_query, \
    build_retrieve_query, search_organizations, retrieve_organization
from ..settings import ES_VARS
from .utils import IterableAttrDict


class GetRorIDTestCase(SimpleTestCase):
    def test_no_id(self):
        self.assertIsNone(get_ror_id('no id here'))
        self.assertIsNone(get_ror_id('http://0w7hudk23'))
        self.assertIsNone(get_ror_id('https://0w7hudk23'))

    def test_extract_id(self):
        self.assertEquals(get_ror_id('0w7hudk23'), 'https://ror.org/0w7hudk23')
        self.assertEquals(get_ror_id('ror.org/0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEquals(get_ror_id('ror.org%2F0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEquals(get_ror_id('http://ror.org/0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEquals(get_ror_id('http%3A%2F%2Fror.org%2F0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEquals(get_ror_id('https://ror.org/0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEquals(get_ror_id('https%3A%2F%2Fror.org%2F0w7hudk23'),
                          'https://ror.org/0w7hudk23')


class ValidationTestCase(SimpleTestCase):
    def test_illegal_parameters(self):
        error = validate({
            'query': 'query',
            'illegal': 'whatever',
            'another': 3
        })
        self.assertEquals(len(error.errors), 2)
        self.assertTrue(any(['illegal' in e for e in error.errors]))
        self.assertTrue(any(['another' in e for e in error.errors]))

    def test_invalid_filter(self):
        error = validate({
            'query': 'query',
            'filter': 'fi1:e,types:F,f3,field2:44'
        })
        self.assertEquals(len(error.errors), 3)
        self.assertTrue(any(['fi1' in e for e in error.errors]))
        self.assertTrue(any(['field2' in e for e in error.errors]))
        self.assertTrue(any(['f3' in e for e in error.errors]))

    def test_invalid_page(self):
        for page in [
                'whatever', '-5', '0',
                str(int(round(10000 / ES_VARS['BATCH_SIZE'])) + 1), '10000'
        ]:
            error = validate({'query': 'query', 'page': page})
            self.assertEquals(len(error.errors), 1)
            self.assertTrue(page in error.errors[0])

    def test_multiple_errors(self):
        error = validate({
            'query': 'query',
            'illegal': 'whatever',
            'filter': 'fi1:e,types:F,f3,field2:44',
            'another': 3,
            'page': 'third'
        })
        self.assertEquals(len(error.errors), 6)
        self.assertTrue(any(['illegal' in e for e in error.errors]))
        self.assertTrue(any(['another' in e for e in error.errors]))
        self.assertTrue(any(['fi1' in e for e in error.errors]))
        self.assertTrue(any(['field2' in e for e in error.errors]))
        self.assertTrue(any(['f3' in e for e in error.errors]))
        self.assertTrue(any(['third' in e for e in error.errors]))

    def test_all_good(self):
        error = validate({
            'query': 'query',
            'page': 4,
            'filter': 'country.country_code:DE,types:s'
        })
        self.assertIsNone(error)


class BuildSearchQueryTestCase(SimpleTestCase):
    def setUp(self):
        self.default_query = \
            {'aggs': {'countries': {'terms': {'field': 'country.country_code',
                                              'min_doc_count': 1, 'size': 10}},
                      'types': {'terms': {'field': 'types', 'min_doc_count': 1,
                                          'size': 10}}}, 'from': 0, 'size': 20}

    def test_empty_query(self):
        query = build_search_query({})
        self.assertEquals(query.to_dict(),
                          dict(self.default_query, query={'match_all': {}}))

    def test_query_id(self):
        expected = dict(self.default_query,
                        query={
                            'match': {
                                'id': {
                                    'query': 'https://ror.org/0w7hudk23',
                                    'operator': 'and'
                                }
                            }
                        })

        query = build_search_query({'query': '0w7hudk23'})
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'ror.org/0w7hudk23'})
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'ror.org%2F0w7hudk23'})
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'http://ror.org/0w7hudk23'})
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query(
            {'query': 'http%3A%2F%2Fror.org%2F0w7hudk23'})
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'https://ror.org/0w7hudk23'})
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query(
            {'query': 'https%3A%2F%2Fror.org%2F0w7hudk23'})
        self.assertEquals(query.to_dict(), expected)

    def test_query(self):
        query = build_search_query({'query': 'query terms'})
        self.assertEquals(
            query.to_dict(),
            dict(self.default_query,
                 query={
                     'query_string': {
                         'query': 'query terms',
                         'fuzzy_max_expansions': 1
                     }
                 }))

    def test_filter(self):
        f = 'key1:val1,k2:value2'
        e = [{'term': {'key1': 'val1'}}, {'term': {'k2': 'value2'}}]

        query = build_search_query({'filter': f})
        self.assertEquals(
            query.to_dict(),
            dict(self.default_query, query={'bool': {
                'filter': e
            }}))

        query = build_search_query({'query': 'query terms', 'filter': f})
        self.assertEquals(
            query.to_dict(),
            dict(self.default_query,
                 query={
                     'bool': {
                         'filter':
                         e,
                         'must': [{
                             'query_string': {
                                 'query': 'query terms',
                                 'fuzzy_max_expansions': 1
                             }
                         }]
                     }
                 }))

    def test_pagination(self):
        base = self.default_query
        base['from'] = 80

        query = build_search_query({'page': '5'})
        self.assertEquals(query.to_dict(), dict(base, query={'match_all': {}}))

        query = build_search_query({'page': '5', 'query': 'query terms'})
        self.assertEquals(
            query.to_dict(),
            dict(base,
                 query={
                     'query_string': {
                         'query': 'query terms',
                         'fuzzy_max_expansions': 1
                     }
                 }))


class BuildRetrieveQueryTestCase(SimpleTestCase):
    def test_retrieve_query(self):
        query = build_retrieve_query('ror-id')
        self.assertEquals(query.to_dict(), {
            'query': {
                'match': {
                    'id': {
                        'operator': 'and',
                        'query': 'ror-id'
                    }
                }
            }
        })


class SearchOrganizationsTestCase(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organizations = search_organizations({})
        self.assertIsNone(error)

        search_mock.assert_called_once()
        self.assertEquals(organizations.number_of_results,
                          self.test_data['hits']['total'])
        self.assertEquals(organizations.time_taken, self.test_data['took'])
        self.assertEquals(len(organizations.items),
                          len(self.test_data['hits']['hits']))
        for ret, exp in zip(organizations.items,
                            self.test_data['hits']['hits']):
            self.assertEquals(ret.id, exp['id'])
            self.assertEquals(ret.name, exp['name'])
        self.assertEquals(
            len(organizations.meta.types),
            len(self.test_data['aggregations']['types']['buckets']))
        for ret, exp in \
                zip(organizations.meta.types,
                    self.test_data['aggregations']['types']['buckets']):
            self.assertEquals(ret.title, exp['key'])
            self.assertEquals(ret.count, exp['doc_count'])
        self.assertEquals(
            len(organizations.meta.countries),
            len(self.test_data['aggregations']['countries']['buckets']))
        for ret, exp in \
                zip(organizations.meta.countries,
                    self.test_data['aggregations']['countries']['buckets']):
            self.assertEquals(ret.id, exp['key'].lower())
            self.assertEquals(ret.count, exp['doc_count'])

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_malformed_search_organizations(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organizations = search_organizations({
            'query': 'query',
            'illegal': 'whatever',
            'filter': 'fi1:e,types:F,f3,field2:44',
            'another': 3,
            'page': 'third'
        })
        self.assertIsNone(organizations)

        search_mock.assert_not_called()
        self.assertEquals(len(error.errors), 6)


class RetrieveOrganizationsTestCase(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_retrieve.json'), 'r') as f:
            self.test_data = json.load(f)
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty.json'), 'r') as f:
            self.test_data_empty = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organization = retrieve_organization('ror-id')
        self.assertIsNone(error)

        search_mock.assert_called_once()
        expected = self.test_data['hits']['hits'][0]
        self.assertEquals(organization.id, expected['id'])
        self.assertEquals(organization.name, expected['name'])

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_non_existing_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])

        error, organization = retrieve_organization('ror-id')
        self.assertIsNone(organization)

        search_mock.assert_called_once()
        self.assertEquals(len(error.errors), 1)
        self.assertTrue('ror-id' in error.errors[0])
