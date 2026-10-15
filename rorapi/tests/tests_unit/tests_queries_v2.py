import json
from unittest import mock
import os

from django.test import SimpleTestCase
from elasticsearch_dsl import Search
from elasticsearch_dsl.response import Response

from rorapi.common.queries import get_ror_id, validate, build_search_query, \
    build_retrieve_query, search_organizations, retrieve_organization, \
    quote_spaced_external_id_values, build_filters, build_typeahead_query
from rorapi.v2.models import TypeaheadResult
from rorapi.settings import ES_VARS
from .utils import IterableAttrDict, effective_timeout, scored_tiers


class GetRorIDTestCase(SimpleTestCase):

    def test_no_id(self):
        self.assertIsNone(get_ror_id('no id here'))
        self.assertIsNone(get_ror_id('http://0w7hudk23'))
        self.assertIsNone(get_ror_id('https://0w7hudk23'))

    def test_extract_id(self):
        self.assertEqual(get_ror_id('0w7hudk23'), 'https://ror.org/0w7hudk23')
        self.assertEqual(get_ror_id('ror.org/0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEqual(get_ror_id('ror.org%2F0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEqual(get_ror_id('http://ror.org/0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEqual(get_ror_id('http%3A%2F%2Fror.org%2F0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEqual(get_ror_id('https://ror.org/0w7hudk23'),
                          'https://ror.org/0w7hudk23')
        self.assertEqual(get_ror_id('https%3A%2F%2Fror.org%2F0w7hudk23'),
                          'https://ror.org/0w7hudk23')


class ValidationTestCase(SimpleTestCase):

    def test_illegal_parameters(self):
        error = validate({
            'query': 'query',
            'illegal': 'whatever',
            'another': 3
        })
        self.assertEqual(len(error.errors), 2)
        self.assertTrue(any(['illegal' in e for e in error.errors]))
        self.assertTrue(any(['another' in e for e in error.errors]))

    def test_invalid_all_status_value(self):
        error = validate({
            'all_status': 'foo'
        })
        self.assertEqual(len(error.errors), 1)
        self.assertTrue(any(['allowed values' in e for e in error.errors]))

    def test_too_many_parameters(self):
        error = validate({
            'query': 'query',
            'query.advanced': 'query'
        })
        self.assertEqual(error.errors, [
            'query and query.advanced parameters cannot be combined. please use either query OR query.advanced'])

    def test_query_modes_exclusive(self):
        for modes in [('query', 'query.typeahead'), ('query.advanced', 'query.typeahead'),
                      ('query', 'query.advanced', 'query.typeahead')]:
            error = validate({m: 'harv' for m in modes})
            self.assertEqual(len(error.errors), 1, modes)
            self.assertIn('cannot be combined', error.errors[0])
            for m in modes:
                self.assertIn(m, error.errors[0])

    def test_invalid_typeahead(self):
        for value in ['**', ' ']:
            error = validate({'query.typeahead': value})
            self.assertEqual(len(error.errors), 1, value)
            self.assertIn('query.typeahead', error.errors[0])

    def test_typeahead_any_length(self):
        self.assertIsNone(validate({'query.typeahead': 'a' * 5000}))

    def test_typeahead_all_good(self):
        self.assertIsNone(validate({
            'query.typeahead': 'Harv',
            'page': '2',
            'page_size': '10',
            'filter': 'types:education',
            'all_status': ''
        }))

    def test_illegal_field(self):
        error = validate({
            'query.advanced': 'foo:bar'
        })
        self.assertEqual(len(error.errors), 1)
        self.assertTrue(any(['illegal' in e for e in error.errors]))

    def test_legacy_external_id_field_hint(self):
        error = validate({
            'query.advanced': 'external_ids.FundRef.all:100000908'
        })
        self.assertEqual(len(error.errors), 1)
        self.assertIn('illegal field name', error.errors[0])
        self.assertIn('external_ids.type', error.errors[0])
        self.assertIn('external_ids.all', error.errors[0])
        self.assertIn('schema v2', error.errors[0])


    def test_invalid_filter(self):
        error = validate({
            'query': 'query',
            'filter': 'fi1:e,types:F,f3,field2:44'
        })
        self.assertEqual(len(error.errors), 3)
        self.assertTrue(any(['fi1' in e for e in error.errors]))
        self.assertTrue(any(['field2' in e for e in error.errors]))
        self.assertTrue(any(['f3' in e for e in error.errors]))

    def test_invalid_page(self):
        for page in [
                'whatever', '-5', '0', '10001'
        ]:
            error = validate({'query': 'query', 'page': page})
            self.assertEqual(len(error.errors), 1)
            self.assertTrue(page in error.errors[0])

    def test_invalid_page_size(self):
        for page_size in ['ten', '0', '-1', str(ES_VARS['BATCH_SIZE'] + 1)]:
            error = validate({'query.typeahead': 'harv', 'page_size': page_size})
            self.assertEqual(len(error.errors), 1)
            self.assertIn("page_size '{}'".format(page_size), error.errors[0])

    def test_valid_page_size(self):
        for page_size in ['1', str(ES_VARS['BATCH_SIZE'])]:
            self.assertIsNone(validate({'query.typeahead': 'harv', 'page_size': page_size}))

    def test_last_page_holds_result_10000(self):
        for page_size, last_page in [
                (1, 10000), (3, 3334), (5, 2000), (15, 667), (20, 500)]:
            params = {'query.typeahead': 'harv', 'page_size': str(page_size)}
            error = validate({**params, 'page': str(last_page + 1)})
            self.assertEqual(error.errors, [
                "page '{}' outside of range 1-{}".format(last_page + 1, last_page)])
            error = validate({**params, 'page': str(last_page)})
            self.assertIsNone(error, error and error.errors)

    def test_page_bound_is_500_at_the_default_page_size(self):
        error = validate({'query': 'query', 'page': '501'})
        self.assertEqual(error.errors, ["page '501' outside of range 1-500"])

    def test_page_bound_with_an_invalid_page_size(self):
        for page_size, page_size_error in [
                ('0', "page_size '0' outside of range 1-20"),
                ('ten', "page_size 'ten' is not an integer")]:
            error = validate(
                {'query.typeahead': 'harv', 'page_size': page_size, 'page': '501'})
            self.assertEqual(
                error.errors, ["page '501' outside of range 1-500", page_size_error])

    def test_page_size_is_illegal_without_typeahead(self):
        for params in [{'query': 'query'}, {'query.advanced': 'names.value:harvard'},
                       {'filter': 'types:education'}, {}]:
            error = validate({**params, 'page_size': '5'})
            self.assertEqual(error.errors, ["query parameter 'page_size' is illegal"], params)

    def test_illegal_page_size_lists_in_parameter_order(self):
        error = validate({'bogus': '1', 'page_size': '5', 'another': '2'})
        self.assertEqual(error.errors, [
            "query parameter 'bogus' is illegal",
            "query parameter 'page_size' is illegal",
            "query parameter 'another' is illegal"])

    def test_illegal_page_size_skips_the_all_status_and_combination_checks(self):
        error = validate({'page_size': '5', 'all_status': 'maybe'})
        self.assertEqual(error.errors, ["query parameter 'page_size' is illegal"])
        error = validate({'query': 'a', 'query.advanced': 'names.value:b', 'page_size': '5'})
        self.assertEqual(error.errors, ["query parameter 'page_size' is illegal"])

    def test_multiple_errors(self):
        error = validate({
            'query': 'query',
            'illegal': 'whatever',
            'filter': 'fi1:e,types:F,f3,field2:44',
            'another': 3,
            'page': 'third'
        })
        self.assertEqual(len(error.errors), 6)
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
            'filter': 'country.country_code:DE,types:s,status:inactive',
            'all_status': ''
        })
        self.assertIsNone(error)

    def test_all_good_country_name(self):
        error = validate({
            'query': 'query',
            'page': 4,
            'filter': 'country.country_name:Germany,types:s,status:inactive',
            'all_status': ''
        })
        self.assertIsNone(error)

    def test_query_adv_no_fields(self):
        error = validate({
            'query.advanced': 'query'
        })
        self.assertIsNone(error)

    def test_query_adv_wildcard(self):
        error = validate({
            'query.advanced': r'locations.\*:bar'
        })
        self.assertIsNone(error)

    def test_query_adv_exists(self):
        error = validate({
            'query.advanced': '_exists_:id'
        })
        self.assertIsNone(error)

    def test_query_adv_esc(self):
        error = validate({
            'query.advanced': r'query\:query'
        })
        self.assertIsNone(error)

    def test_query__all_status(self):
        error = validate({
            'query': 'query',
            'all_status': ''
        })
        self.assertIsNone(error)

    def test_query_adv_no_fields_all_status(self):
        error = validate({
            'query.advanced': 'query',
            'all_status': ''
        })
        self.assertIsNone(error)

    def test_no_query_all_status(self):
        error = validate({
            'all_status': ''
        })
        self.assertIsNone(error)

class BuildSearchQueryTestCase(SimpleTestCase):

    def setUp(self):
        self.default_query = \
                {'aggs': {'types': {'terms': {'field': 'types.raw', 'size': 10, 'min_doc_count': 1}},
                'countries': {'terms': {'field': 'locations.geonames_details.country_code.raw', 'size': 10, 'min_doc_count': 1}},
                'continents': {'terms': {'field': 'locations.geonames_details.continent_code.raw', 'size': 10, 'min_doc_count': 1}},
                'statuses': {'terms': {'field': 'status.raw', 'size': 10, 'min_doc_count': 1}}},
                'track_total_hits': True, 'from': 0, 'size': 20}

    def test_no_sort_outside_typeahead(self):
        for params in [{}, {'query': 'harvard'}, {'query.advanced': 'names.value:harvard'},
                       {'filter': 'types:education'}, {'all_status': ''}]:
            self.assertNotIn('sort', build_search_query(params).to_dict(), params)

    def test_empty_query_default(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({})
        self.assertEqual(query.to_dict(), expected)

    def test_empty_query_all_status(self):
        expected = {'query': {'match_all': {}}, 'track_total_hits': True}
        expected.update(self.default_query)
        query = build_search_query({'all_status':''})
        self.assertEqual(query.to_dict(), expected)

    def test_empty_query_all_status_false(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'all_status':'false'})
        self.assertEqual(query.to_dict(), expected)

    def test_query_id(self):
        expected = {'query': {
                        'match': {
                            'id': {
                                'query': 'https://ror.org/0w7hudk23',
                                'operator': 'and'
                            }
                        }
                    }}

        expected.update(self.default_query)

        query = build_search_query({'query': '0w7hudk23'})
        self.assertEqual(query.to_dict(), expected)
        query = build_search_query({'query': 'ror.org/0w7hudk23'})
        self.assertEqual(query.to_dict(), expected)
        query = build_search_query({'query': 'ror.org%2F0w7hudk23'})
        self.assertEqual(query.to_dict(), expected)
        query = build_search_query({'query': 'http://ror.org/0w7hudk23'})
        self.assertEqual(query.to_dict(), expected)
        query = build_search_query(
            {'query': 'http%3A%2F%2Fror.org%2F0w7hudk23'})
        self.assertEqual(query.to_dict(), expected)
        query = build_search_query({'query': 'https://ror.org/0w7hudk23'})
        self.assertEqual(query.to_dict(), expected)
        query = build_search_query(
            {'query': 'https%3A%2F%2Fror.org%2F0w7hudk23'})
        self.assertEqual(query.to_dict(), expected)

    def test_query_default(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}],
                'must': [{'nested': {
                    'path': 'names_ids',
                    'score_mode': 'max',
                    'query': {
                        'query_string': {
                            'query': 'query terms',
                            'fields': ['names_ids.name', 'names_ids.id'],
                            'lenient': True,
                            'fuzzy_max_expansions': 1
                        }
                    }
                }}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms'})
        self.assertEqual(query.to_dict(), expected)

    def test_query_all_status(self):
        expected = {'query': {
            'nested': {
                    'path': 'names_ids',
                    'score_mode': 'max',
                    'query': {
                        'query_string': {
                            'query': 'query terms',
                            'fields': ['names_ids.name', 'names_ids.id'],
                            'lenient': True,
                            'fuzzy_max_expansions': 1
                        }
                    }
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'all_status': ''})
        self.assertEqual(query.to_dict(), expected)

    def test_query_advanced(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}],
                'must': [{
                    'query_string': {
                        'query': 'query terms',
                        'default_field': '*',
                        'default_operator':'and',
                        'fuzzy_max_expansions': 1
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query.advanced': 'query terms'})
        self.assertEqual(query.to_dict(), expected)

    def test_quote_spaced_external_id_values_helper(self):
        self.assertEqual(
            quote_spaced_external_id_values(
                'external_ids.all:0000 0001 2375 2908'),
            'external_ids.all:"0000 0001 2375 2908"')
        self.assertEqual(
            quote_spaced_external_id_values(
                'external_ids.all:"0000 0001 2375 2908"'),
            'external_ids.all:"0000 0001 2375 2908"')
        self.assertEqual(
            quote_spaced_external_id_values('external_ids.all:100000908'),
            'external_ids.all:100000908')
        self.assertEqual(
            quote_spaced_external_id_values(
                'external_ids.all:0000 0001 2375 2908 AND status:active'),
            'external_ids.all:"0000 0001 2375 2908" AND status:active')

    def test_query_advanced_quotes_spaced_external_ids(self):
        query = build_search_query({
            'query.advanced': 'external_ids.all:0000 0001 2375 2908'
        }).to_dict()
        self.assertEqual(
            query['query']['bool']['must'][0]['query_string']['query'],
            'external_ids.all:"0000 0001 2375 2908"')

    def test_query_advanced_nfc_normalization(self):
        nfd = 'locations.geonames_details.name:Hu\u0065\u0302\u0301'
        nfc_form = 'locations.geonames_details.name:Hu\u1ebf'
        self.assertNotEqual(nfd, nfc_form)
        query = build_search_query({'query.advanced': nfd}).to_dict()
        self.assertEqual(
            query['query']['bool']['must'][0]['query_string']['query'], nfc_form)

    def test_query_nfc_normalization(self):
        query = build_search_query({'query': 'Montre\u0301al'}).to_dict()
        self.assertEqual(
            query['query']['bool']['must'][0]['nested']['query']['query_string']['query'],
            'Montr\u00e9al')

    def test_filter_nfc_normalization(self):
        query = build_search_query({
            'filter': 'locations.geonames_details.country_name:Cura\u0063\u0327ao',
            'all_status': ''
        }).to_dict()
        self.assertIn(
            {'terms': {'locations.geonames_details.country_name': ('Cura\u00e7ao',)}},
            query['query']['bool']['filter'])

    def test_aggregations_use_raw_subfields(self):
        aggs = build_search_query({}).to_dict()['aggs']
        self.assertEqual(aggs['types']['terms']['field'], 'types.raw')
        self.assertEqual(aggs['countries']['terms']['field'],
                         'locations.geonames_details.country_code.raw')
        self.assertEqual(aggs['continents']['terms']['field'],
                         'locations.geonames_details.continent_code.raw')
        self.assertEqual(aggs['statuses']['terms']['field'], 'status.raw')

    def test_query_advanced_all_status(self):
        expected = {'query': {
            'bool': {
                'must': [{
                    'query_string': {
                        'query': 'query terms',
                        'default_field': '*',
                        'default_operator':'and',
                        'fuzzy_max_expansions': 1
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query.advanced': 'query terms', 'all_status': ''})
        self.assertEqual(query.to_dict(), expected)

    def test_query_advanced_status_filter(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ('inactive',)}}],
                'must': [{
                    'query_string': {
                        'query': 'query terms',
                        'default_field': '*',
                        'default_operator':'and',
                        'fuzzy_max_expansions': 1
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        f = 'status:inactive'
        query = build_search_query({'query.advanced': 'query terms', 'filter': f})
        self.assertEqual(query.to_dict(), expected)

    def test_query_advanced_status_field(self):
        expected = {'query': {
            'bool': {
                'must': [{
                    'query_string': {
                        'query': 'status:inactive',
                        'default_field': '*',
                        'default_operator':'and',
                        'fuzzy_max_expansions': 1
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query.advanced': 'status:inactive'})
        self.assertEqual(query.to_dict(), expected)

    def test_filter(self):
        f = 'key1:val1,k2:value2'
        expected = {'query': {
            'bool': {
                'filter': [
                    {'terms': {'key1': ('val1',)}},
                    {'terms': {'k2': ('value2',)}},
                    {'terms': {'status': ['active']}}
                ],
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'filter': f})
        self.assertEqual(query.to_dict(), expected)

    def test_filter_status_filter(self):
        f = 'key1:val1,k2:value2,status:inactive'
        expected = {'query': {
            'bool': {
                'filter': [
                    {'terms': {'key1': ('val1',)}},
                    {'terms': {'k2': ('value2',)}},
                    {'terms': {'status': ('inactive',)}}
                ],
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'filter': f})
        self.assertEqual(query.to_dict(), expected)

    def test_filter_whitespace_normalization(self):
        f = 'locations.geonames_details.country_name:South  Africa'
        expected = {'query': {
            'bool': {
                'filter': [
                    {'terms': {'locations.geonames_details.country_name': ('South Africa',)}},
                    {'terms': {'status': ['active']}}
                ],
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'filter': f})
        self.assertEqual(query.to_dict(), expected)

    def test_filter_all_status(self):
        f = 'key1:val1,k2:value2'
        expected = {'query': {
            'bool': {
                'filter': [
                    {'terms': {'key1': ('val1',)}},
                    {'terms': {'k2': ('value2',)}},
                ],
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'filter': f, 'all_status': ''})
        self.assertEqual(query.to_dict(), expected)

    def test_filter_query(self):
        f = 'key1:val1,k2:value2'
        expected = {'query': {
            'bool': {
                'filter': [
                    {'terms': {'key1': ('val1',)}},
                    {'terms': {'k2': ('value2',)}},
                    {'terms': {'status': ['active']}}
                ],
                'must': [{
                    'nested': {
                        'path': 'names_ids',
                        'score_mode': 'max',
                        'query': {
                            'query_string': {
                                'query': 'query terms',
                                'fields': ['names_ids.name', 'names_ids.id'],
                                'lenient': True,
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'filter': f})
        self.assertEqual(query.to_dict(), expected)

    def test_filter_query_all_status(self):
        f = 'key1:val1,k2:value2'
        expected = {'query': {
            'bool': {
                'filter': [
                    {'terms': {'key1': ('val1',)}},
                    {'terms': {'k2': ('value2',)}},
                ],
                'must': [{
                    'nested': {
                        'path': 'names_ids',
                        'score_mode': 'max',
                        'query': {
                            'query_string': {
                                'query': 'query terms',
                                'fields': ['names_ids.name', 'names_ids.id'],
                                'lenient': True,
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'filter': f, 'all_status': ''})
        self.assertEqual(query.to_dict(), expected)

    def test_pagination(self):
        expected = {'query': {'bool': {'filter': [{'terms': {'status': ['active']}}]}}}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5'})
        self.assertEqual(query.to_dict(), expected)

    def test_pagination_all_status(self):
        expected = {'query': {'match_all': {}}}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'all_status': ''})
        self.assertEqual(query.to_dict(), expected)

    def test_pagination_query(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}],
                'must': [{
                    'nested': {
                        'path': 'names_ids',
                        'score_mode': 'max',
                        'query': {
                            'query_string': {
                                'query': 'query terms',
                                'fields': ['names_ids.name', 'names_ids.id'],
                                'lenient': True,
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'query': 'query terms'})
        self.assertEqual(query.to_dict(), expected)

    def test_pagination_query_all_status(self):
        expected = {'query': {
            'nested': {
                        'path': 'names_ids',
                        'score_mode': 'max',
                        'query': {
                            'query_string': {
                                'query': 'query terms',
                                'fields': ['names_ids.name', 'names_ids.id'],
                                'lenient': True,
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
            }}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'query': 'query terms', 'all_status': ''})
        self.assertEqual(query.to_dict(), expected)


class BuildFiltersTestCase(SimpleTestCase):

    def test_default_status_active(self):
        self.assertEqual(build_filters({}), {'status': ['active']})
        self.assertEqual(build_filters({'all_status': 'false'}), {'status': ['active']})
        self.assertEqual(build_filters({'query': 'q'}), {'status': ['active']})

    def test_no_default_status(self):
        self.assertEqual(build_filters({'all_status': ''}), {})
        self.assertEqual(build_filters({'all_status': 'True'}), {})
        self.assertEqual(build_filters({}, ror_id='https://ror.org/0w7hudk23'), {})
        self.assertEqual(build_filters({'query.advanced': 'status:inactive'}), {})
        self.assertEqual(build_filters({'filter': 'status:Withdrawn'}), {'status': ('withdrawn',)})

    def test_filter_values_normalized(self):
        self.assertEqual(
            build_filters({'filter': 'types:Education,types:facility', 'all_status': ''}),
            {'types': ('education', 'facility')})

    def test_params_not_mutated(self):
        params = {'all_status': 'false', 'filter': 'types:education'}
        build_filters(params)
        self.assertEqual(params, {'all_status': 'false', 'filter': 'types:education'})


class BuildTypeaheadQueryTestCase(SimpleTestCase):

    def test_filters_paging_and_no_aggregations(self):
        query = build_typeahead_query({
            'query.typeahead': 'Harv', 'filter': 'types:Education', 'page': '2', 'page_size': '5'
        }).to_dict()
        self.assertEqual(query['query']['bool']['filter'], [
            {'terms': {'types': ('education',)}},
            {'terms': {'status': ['active']}},
        ])
        self.assertEqual(query['query']['bool']['must'][0]['nested']['path'], 'names_ids')
        self.assertNotIn('aggs', query)
        self.assertEqual(query['track_total_hits'], 10000)
        self.assertEqual((query['from'], query['size']), (5, 5))

    def test_all_status_drops_default_status(self):
        query = build_typeahead_query({'query.typeahead': 'Harv', 'all_status': ''}).to_dict()
        self.assertNotIn('bool', query['query'])
        self.assertEqual((query['from'], query['size']), (0, 20))

    def tiers_and_filters(self, params):
        query = build_typeahead_query(params).to_dict()['query']
        bool_query = query.get('bool', {'must': [query]})
        return [f for _, f in scored_tiers(bool_query['must'][0])], bool_query.get('filter', [])

    def test_ror_id_looks_up_the_canonical_id_in_any_status(self):
        for spelling in ['02v6kpv12', ' 02v6kpv12 ', 'ror.org/02v6kpv12', 'ror.org%2F02v6kpv12',
                         'http://ror.org/02v6kpv12', 'http%3A%2F%2Fror.org%2F02v6kpv12',
                         'https://ror.org/02v6kpv12', 'https%3A%2F%2Fror.org%2F02v6kpv12']:
            self.assertEqual(self.tiers_and_filters({'query.typeahead': spelling}),
                             ([{'term': {'names_ids.id': 'https://ror.org/02v6kpv12'}}], []), spelling)

    def test_ror_id_keeps_explicit_filters(self):
        self.assertEqual(
            self.tiers_and_filters({'query.typeahead': '02v6kpv12', 'filter': 'types:Education'})[1],
            [{'terms': {'types': ('education',)}}])
        self.assertEqual(
            self.tiers_and_filters({'query.typeahead': '02v6kpv12', 'filter': 'status:active'})[1],
            [{'terms': {'status': ('active',)}}])

    def test_ror_id_lookup_keeps_paging_inner_hits_and_the_count_cap(self):
        query = build_typeahead_query({
            'query.typeahead': '02v6kpv12', 'page': '2', 'page_size': '5'
        }).to_dict()
        nested = query['query'].get('bool', {'must': [query['query']]})['must'][0]['nested']
        self.assertEqual(nested['inner_hits']['name'], 'matched_name')
        self.assertNotIn('aggs', query)
        self.assertEqual(query['track_total_hits'], 10000)
        self.assertEqual((query['from'], query['size']), (5, 5))

    def test_other_text_runs_the_name_tiers_under_the_default_status(self):
        for text in ['grid.38142.3c', 'Q13371', '0000 0001 2375 2908', '03vek6s5', 'Harv']:
            tiers, filters = self.tiers_and_filters({'query.typeahead': text})
            self.assertGreater(len(tiers), 1, text)
            self.assertIn({'term': {'names_ids.id': text}}, tiers[0]['bool']['should'], text)
            self.assertEqual(filters, [{'terms': {'status': ['active']}}], text)


class BuildRetrieveQueryTestCase(SimpleTestCase):

    def test_retrieve_query(self):
        query = build_retrieve_query('ror-id')
        self.assertEqual(query.to_dict(), {
            'query': {
                'match': {
                    'id': {
                        'operator': 'and',
                        'query': 'ror-id'
                    }
                }
            },
            'track_total_hits': True
        })

class SearchOrganizationsTestCase(SimpleTestCase):

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es7_v2.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organizations = search_organizations({})
        self.assertIsNone(error)

        search_mock.assert_called_once()
        self.assertEqual(organizations.number_of_results,
                          self.test_data['hits']['total']['value'])
        self.assertEqual(organizations.time_taken, self.test_data['took'])
        self.assertEqual(len(organizations.items),
                          len(self.test_data['hits']['hits']))
        for ret, exp in zip(organizations.items,
                            self.test_data['hits']['hits']):
            self.assertEqual(ret.id, exp['_source']['id'])
            for i, name in enumerate(ret.names):
                matched_names = [n for n in exp['_source']['names'] if \
                                    n['value']==ret.names[i].value and \
                                    n['types']==ret.names[i].types and \
                                    n['lang']==ret.names[i].lang]
                self.assertTrue(len(matched_names) == 1)
        self.assertEqual(
            len(organizations.meta.types),
            len(self.test_data['aggregations']['types']['buckets']))
        for ret, exp in \
                zip(organizations.meta.types,
                    self.test_data['aggregations']['types']['buckets']):
            self.assertEqual(ret.title, exp['key'])
            self.assertEqual(ret.count, exp['doc_count'])
        self.assertEqual(
            len(organizations.meta.countries),
            len(self.test_data['aggregations']['countries']['buckets']))
        for ret, exp in \
                zip(organizations.meta.countries,
                    self.test_data['aggregations']['countries']['buckets']):
            self.assertEqual(ret.id, exp['key'].lower())
            self.assertEqual(ret.count, exp['doc_count'])
        self.assertEqual(
            len(organizations.meta.continents),
            len(self.test_data['aggregations']['continents']['buckets']))
        for ret, exp in \
                zip(organizations.meta.continents,
                    self.test_data['aggregations']['continents']['buckets']):
            self.assertEqual(ret.id, exp['key'].lower())
            self.assertEqual(ret.count, exp['doc_count'])
        self.assertEqual(
            len(organizations.meta.statuses),
            len(self.test_data['aggregations']['statuses']['buckets']))
        for ret, exp in \
                zip(organizations.meta.statuses,
                    self.test_data['aggregations']['statuses']['buckets']):
            self.assertEqual(ret.id, exp['key'].lower())
            self.assertEqual(ret.count, exp['doc_count'])

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
        self.assertEqual(len(error.errors), 6)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations_request_error(self, search_mock):
        from elasticsearch.exceptions import RequestError

        search_mock.side_effect = RequestError(
            400,
            'parsing_exception',
            {'error': {'type': 'parsing_exception', 'reason': 'bad query'}},
        )

        error, organizations = search_organizations({'query': 'query'})
        self.assertIsNone(organizations)
        search_mock.assert_called_once()
        self.assertEqual(len(error.errors), 1)
        self.assertTrue('parsing_exception' in error.errors[0])

    @mock.patch('elasticsearch.RequestsHttpConnection.perform_request', autospec=True)
    def test_search_organizations_uses_the_240_second_client(self, perform_request):
        perform_request.return_value = (200, {}, json.dumps(self.test_data))

        error, _ = search_organizations({'query': 'query'})

        self.assertIsNone(error)
        perform_request.assert_called_once()
        self.assertEqual(effective_timeout(perform_request.call_args), 240)
        _, _, _, params, _ = perform_request.call_args.args
        self.assertEqual(params['search_type'], b'dfs_query_then_fetch')


class SearchOrganizationsTypeaheadTestCase(SimpleTestCase):

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_typeahead_es7_v2.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations_typeahead(self, search_mock):
        search_mock.return_value = Response(Search(index='organizations-v2'), self.test_data)

        error, result = search_organizations({'query.typeahead': 'Harv'})
        self.assertIsNone(error)

        search_mock.assert_called_once()
        self.assertIsInstance(result, TypeaheadResult)

    @mock.patch('elasticsearch.RequestsHttpConnection.perform_request', autospec=True)
    def test_search_organizations_typeahead_has_a_2_second_budget(self, perform_request):
        perform_request.return_value = (200, {}, json.dumps(self.test_data))

        error, result = search_organizations({'query.typeahead': 'Harv'})

        self.assertIsNone(error)
        self.assertEqual(result.number_of_results, 3)
        perform_request.assert_called_once()
        self.assertEqual(effective_timeout(perform_request.call_args), 2)
        _, _, _, params, _ = perform_request.call_args.args
        self.assertEqual(params['search_type'], b'dfs_query_then_fetch')


class RetrieveOrganizationsTestCase(SimpleTestCase):

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_retrieve_es7_v2.json'), 'r') as f:
            self.test_data = json.load(f)
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es7.json'), 'r') as f:
            self.test_data_empty = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organization = retrieve_organization('ror-id')
        self.assertIsNone(error)

        search_mock.assert_called_once()
        expected = self.test_data['hits']['hits'][0]['_source']
        self.assertEqual(organization.id, expected['id'])
        for i, name in enumerate(organization.names):
            matched_names = [n for n in expected["names"] if \
                                n['value']==organization.names[i].value and \
                                n['types']==organization.names[i].types and \
                                n['lang']==organization.names[i].lang]
            self.assertTrue(len(matched_names) == 1)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_non_existing_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])

        error, organization = retrieve_organization('ror-id')
        self.assertIsNone(organization)

        search_mock.assert_called_once()
        self.assertEqual(len(error.errors), 1)
        self.assertTrue('ror-id' in error.errors[0])
