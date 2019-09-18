from django.test import SimpleTestCase
from ..es_utils import ESQueryBuilder


class QueryBuilderTestCase(SimpleTestCase):
    def test_id_query(self):
        qb = ESQueryBuilder()
        qb.add_id_query('ror-id')

        self.assertEqual(qb.get_query().to_dict(), {
            'query': {
                'match': {
                    'id': {
                        'query': 'ror-id',
                        'operator': 'and'
                    }
                }
            }
        })

    def test_match_all_query(self):
        qb = ESQueryBuilder()
        qb.add_match_all_query()

        self.assertEqual(qb.get_query().to_dict(),
                         {'query': {
                             'match_all': {}
                         }})

    def test_string_query(self):
        qb = ESQueryBuilder()
        qb.add_string_query('query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'query_string': {
                        'query': 'query terms',
                        'fuzzy_max_expansions': 1
                    }
                }
            })

    def test_phrase_query(self):
        qb = ESQueryBuilder()
        qb.add_phrase_query(['f1', 'f2'], 'query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'dis_max': {
                        'queries': [{
                            'match_phrase': {
                                'f1': 'query terms'
                            }
                        }, {
                            'match_phrase': {
                                'f2': 'query terms'
                            }
                        }]
                    }
                }
            })

    def test_common_query(self):
        qb = ESQueryBuilder()
        qb.add_common_query(['f1', 'f2'], 'query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'dis_max': {
                        'queries': [{
                            'common': {
                                'f1': {
                                    'query': 'query terms',
                                    'cutoff_frequency': 0.001
                                }
                            }
                        }, {
                            'common': {
                                'f2': {
                                    'query': 'query terms',
                                    'cutoff_frequency': 0.001
                                }
                            }
                        }]
                    }
                }
            })

    def test_match_query(self):
        qb = ESQueryBuilder()
        qb.add_match_query('query terms')

        self.assertEqual(qb.get_query().to_dict(),
                         {'query': {
                             'match': {
                                 'acronyms': 'query terms'
                             }
                         }})

    def test_fuzzy_query(self):
        qb = ESQueryBuilder()
        qb.add_fuzzy_query(['f1', 'f2'], 'query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'dis_max': {
                        'queries': [{
                            'match': {
                                'f1': {
                                    'query': 'query terms',
                                    'fuzziness': 'AUTO'
                                }
                            }
                        }, {
                            'match': {
                                'f2': {
                                    'query': 'query terms',
                                    'fuzziness': 'AUTO'
                                }
                            }
                        }]
                    }
                }
            })

    def test_add_filters(self):
        qb = ESQueryBuilder()
        qb.add_match_all_query()
        qb.add_filters([('key1', 'val1'), ('k2', 'value2')])

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'bool': {
                        'filter': [{
                            'term': {
                                'key1': 'val1'
                            }
                        }, {
                            'term': {
                                'k2': 'value2'
                            }
                        }]
                    }
                }
            })

    def test_add_aggregations(self):
        qb = ESQueryBuilder()
        qb.add_match_all_query()
        qb.add_aggregations([('countries', 'code'), ('types', 'type')])

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'match_all': {}
                },
                'aggs': {
                    'countries': {
                        'terms': {
                            'field': 'code',
                            'min_doc_count': 1,
                            'size': 10
                        }
                    },
                    'types': {
                        'terms': {
                            'field': 'type',
                            'min_doc_count': 1,
                            'size': 10
                        }
                    }
                }
            })

    def test_paginate(self):
        qb = ESQueryBuilder()
        qb.add_match_all_query()
        qb.paginate(10)

        self.assertEqual(qb.get_query().to_dict(), {
            'query': {
                'match_all': {}
            },
            'from': 180,
            'size': 20
        })
