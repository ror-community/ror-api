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

    def test_invalid_all_status_value(self):
        error = validate({
            'all_status': 'foo'
        })
        self.assertEquals(len(error.errors), 1)
        self.assertTrue(any(['allowed values' in e for e in error.errors]))

    def test_too_many_parameters(self):
        error = validate({
            'query': 'query',
            'query.advanced': 'query'
        })
        self.assertEquals(len(error.errors), 1)
        self.assertTrue(any(['combined' in e for e in error.errors]))

    def test_illegal_field(self):
        error = validate({
            'query.advanced': 'foo:bar'
        })
        self.assertEquals(len(error.errors), 1)
        self.assertTrue(any(['illegal' in e for e in error.errors]))


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
                str(ES_VARS['MAX_PAGE'] + 1), '10001'
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
            'query.advanced': 'addresses.\*:bar'
        })
        self.assertIsNone(error)

    def test_query_adv_exists(self):
        error = validate({
            'query.advanced': '_exists_:id'
        })
        self.assertIsNone(error)

    def test_query_adv_esc(self):
        error = validate({
            'query.advanced': 'query\:query'
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

class BuildSearchQueryTestCaseEs6(SimpleTestCase):
    ENABLE_ES_7 = False

    def setUp(self):
        self.default_query = \
                {'aggs': {'types': {'terms': {'field': 'types', 'size': 10, 'min_doc_count': 1}},
                'countries': {'terms': {'field': 'country.country_code', 'size': 10, 'min_doc_count': 1}},
                'statuses': {'terms': {'field': 'status', 'size': 10, 'min_doc_count': 1}}}, 'from': 0, 'size': 20}

    def test_empty_query_default(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_empty_query_all_status(self):
        expected = {'query': {'match_all': {}}}
        expected.update(self.default_query)
        query = build_search_query({'all_status':''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_empty_query_all_status_false(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'all_status':'false'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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

        query = build_search_query({'query': '0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'ror.org/0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'ror.org%2F0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'http://ror.org/0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query(
            {'query': 'http%3A%2F%2Fror.org%2F0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'https://ror.org/0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query(
            {'query': 'https%3A%2F%2Fror.org%2F0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
                            'fuzzy_max_expansions': 1
                        }
                    }
                }}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_query_all_status(self):
        expected = {'query': {
            'nested': {
                    'path': 'names_ids',
                    'score_mode': 'max',
                    'query': {
                        'query_string': {
                            'query': 'query terms',
                            'fuzzy_max_expansions': 1
                        }
                    }
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'query.advanced': 'query terms'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'query.advanced': 'query terms', 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'query.advanced': 'query terms', 'filter': f}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'query.advanced': 'status:inactive'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'filter': f}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'filter': f}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'filter': f, 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'filter': f}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'filter': f, 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_pagination(self):
        expected = {'query': {'bool': {'filter': [{'terms': {'status': ['active']}}]}}}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_pagination_all_status(self):
        expected = {'query': {'match_all': {}}}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'query': 'query terms'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_pagination_query_all_status(self):
        expected = {'query': {
            'nested': {
                        'path': 'names_ids',
                        'score_mode': 'max',
                        'query': {
                            'query_string': {
                                'query': 'query terms',
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
            }}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'query': 'query terms', 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)


class BuildSearchQueryTestCaseEs7(SimpleTestCase):

    ENABLE_ES_7 = True

    def setUp(self):
        self.default_query = \
                {'aggs': {'types': {'terms': {'field': 'types', 'size': 10, 'min_doc_count': 1}},
                'countries': {'terms': {'field': 'country.country_code', 'size': 10, 'min_doc_count': 1}},
                'statuses': {'terms': {'field': 'status', 'size': 10, 'min_doc_count': 1}}}, 'track_total_hits': True, 'from': 0, 'size': 20}

    def test_empty_query_default(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_empty_query_all_status(self):
        expected = {'query': {'match_all': {}}, 'track_total_hits': True}
        expected.update(self.default_query)
        query = build_search_query({'all_status':''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_empty_query_all_status_false(self):
        expected = {'query': {
            'bool': {
                'filter': [{'terms': {'status': ['active']}}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'all_status':'false'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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

        query = build_search_query({'query': '0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'ror.org/0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'ror.org%2F0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'http://ror.org/0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query(
            {'query': 'http%3A%2F%2Fror.org%2F0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query({'query': 'https://ror.org/0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)
        query = build_search_query(
            {'query': 'https%3A%2F%2Fror.org%2F0w7hudk23'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
                            'fuzzy_max_expansions': 1
                        }
                    }
                }}]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_query_all_status(self):
        expected = {'query': {
            'nested': {
                    'path': 'names_ids',
                    'score_mode': 'max',
                    'query': {
                        'query_string': {
                            'query': 'query terms',
                            'fuzzy_max_expansions': 1
                        }
                    }
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'query.advanced': 'query terms'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'query.advanced': 'query terms', 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'query.advanced': 'query terms', 'filter': f}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'query.advanced': 'status:inactive'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'filter': f}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'filter': f}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
        query = build_search_query({'filter': f, 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'filter': f}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        query = build_search_query({'query': 'query terms', 'filter': f, 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_pagination(self):
        expected = {'query': {'bool': {'filter': [{'terms': {'status': ['active']}}]}}}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_pagination_all_status(self):
        expected = {'query': {'match_all': {}}}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

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
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
                }]
            }
        }}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'query': 'query terms'}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

    def test_pagination_query_all_status(self):
        expected = {'query': {
            'nested': {
                        'path': 'names_ids',
                        'score_mode': 'max',
                        'query': {
                            'query_string': {
                                'query': 'query terms',
                                'fuzzy_max_expansions': 1
                            }
                        }
                    }
            }}
        expected.update(self.default_query)
        expected['from'] = 80
        query = build_search_query({'page': '5', 'query': 'query terms', 'all_status': ''}, self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), expected)

class BuildRetrieveQueryTestCaseEs6(SimpleTestCase):

    ENABLE_ES_7 = False

    def test_retrieve_query(self):
        query = build_retrieve_query('ror-id', self.ENABLE_ES_7)
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


class BuildRetrieveQueryTestCaseEs7(SimpleTestCase):

    ENABLE_ES_7 = True

    def test_retrieve_query(self):
        query = build_retrieve_query('ror-id', self.ENABLE_ES_7)
        self.assertEquals(query.to_dict(), {
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

class SearchOrganizationsTestCaseEs6(SimpleTestCase):
    ENABLE_ES_7 = False
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es6.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organizations = search_organizations({}, self.ENABLE_ES_7)
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
        self.assertEquals(
            len(organizations.meta.statuses),
            len(self.test_data['aggregations']['statuses']['buckets']))
        for ret, exp in \
                zip(organizations.meta.statuses,
                    self.test_data['aggregations']['statuses']['buckets']):
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
        }, self.ENABLE_ES_7)
        self.assertIsNone(organizations)

        search_mock.assert_not_called()
        self.assertEquals(len(error.errors), 6)

class SearchOrganizationsTestCaseEs7(SimpleTestCase):
    ENABLE_ES_7 = True

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es7.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organizations = search_organizations({}, self.ENABLE_ES_7)
        self.assertIsNone(error)

        search_mock.assert_called_once()
        self.assertEquals(organizations.number_of_results,
                          self.test_data['hits']['total']['value'])
        self.assertEquals(organizations.time_taken, self.test_data['took'])
        self.assertEquals(len(organizations.items),
                          len(self.test_data['hits']['hits']))
        for ret, exp in zip(organizations.items,
                            self.test_data['hits']['hits']):
            self.assertEquals(ret.id, exp['_source']['id'])
            self.assertEquals(ret.name, exp['_source']['name'])
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
        self.assertEquals(
            len(organizations.meta.statuses),
            len(self.test_data['aggregations']['statuses']['buckets']))
        for ret, exp in \
                zip(organizations.meta.statuses,
                    self.test_data['aggregations']['statuses']['buckets']):
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
        }, self.ENABLE_ES_7)
        self.assertIsNone(organizations)

        search_mock.assert_not_called()
        self.assertEquals(len(error.errors), 6)

class RetrieveOrganizationsTestCaseEs6(SimpleTestCase):
    ENABLE_ES_7 = False

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_retrieve_es6.json'), 'r') as f:
            self.test_data = json.load(f)
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es6.json'), 'r') as f:
            self.test_data_empty = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organization = retrieve_organization('ror-id', self.ENABLE_ES_7)
        print(error)
        print(organization)
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

        error, organization = retrieve_organization('ror-id', self.ENABLE_ES_7)
        self.assertIsNone(organization)

        search_mock.assert_called_once()
        self.assertEquals(len(error.errors), 1)
        self.assertTrue('ror-id' in error.errors[0])


class RetrieveOrganizationsTestCaseEs7(SimpleTestCase):
    ENABLE_ES_7 = True

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_retrieve_es7.json'), 'r') as f:
            self.test_data = json.load(f)
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es7.json'), 'r') as f:
            self.test_data_empty = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        error, organization = retrieve_organization('ror-id', self.ENABLE_ES_7)
        print(error)
        print(organization)
        self.assertIsNone(error)

        search_mock.assert_called_once()
        expected = self.test_data['hits']['hits'][0]['_source']
        self.assertEquals(organization.id, expected['id'])
        self.assertEquals(organization.name, expected['name'])

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_non_existing_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])

        error, organization = retrieve_organization('ror-id', self.ENABLE_ES_7)
        self.assertIsNone(organization)

        search_mock.assert_called_once()
        self.assertEquals(len(error.errors), 1)
        self.assertTrue('ror-id' in error.errors[0])
