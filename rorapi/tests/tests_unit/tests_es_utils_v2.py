from django.test import SimpleTestCase
from rorapi.common import typeahead
from rorapi.common.es_utils import ESQueryBuilder
from rorapi.settings import ES7_TYPEAHEAD

class QueryBuilderTestCaseV2(SimpleTestCase):
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
            },
            'track_total_hits': True
        })

    def test_match_all_query(self):
        qb = ESQueryBuilder()
        qb.add_match_all_query()

        self.assertEqual(qb.get_query().to_dict(),
                         {'query': {
                             'match_all': {}
                         },
                         'track_total_hits': True
                         })

    def test_string_query(self):
        qb = ESQueryBuilder()
        qb.add_string_query('query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
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
                },
                'track_total_hits': True
            })
    def test_string_query_advanced(self):
        qb = ESQueryBuilder()
        qb.add_string_query_advanced('query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
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
                },
                'track_total_hits': True
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
                },
                'track_total_hits': True
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
                },
                'track_total_hits': True
            })

    def test_match_query(self):
        qb = ESQueryBuilder()
        qb.add_match_query('query terms')

        self.assertEqual(qb.get_query().to_dict(),
                         {'query': {
                             'match': {
                                 'acronyms': 'query terms'
                             }
                         },
                         'track_total_hits': True
                         })

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
                },
                'track_total_hits': True
            })

    def test_phrase_query_affiliation_names(self):
        qb = ESQueryBuilder()
        qb.add_phrase_query_affiliation_names('query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'nested': {
                        'path': 'affiliation_match.names',
                        'score_mode': 'max',
                        'query': {
                            'match_phrase': {
                                'affiliation_match.names.name': 'query terms'
                            }
                        }
                    }
                },
                'track_total_hits': True
            })

    def test_common_query_affiliation_names(self):
        qb = ESQueryBuilder()
        qb.add_common_query_affiliation_names('query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'nested': {
                        'path': 'affiliation_match.names',
                        'score_mode': 'max',
                        'query': {
                            'common': {
                                'affiliation_match.names.name': {
                                    'query': 'query terms',
                                    'cutoff_frequency': 0.001
                                }
                            }
                        }
                    }
                },
                'track_total_hits': True
            })

    def test_fuzzy_query_affiliation_names(self):
        qb = ESQueryBuilder()
        qb.add_fuzzy_query_affiliation_names('query terms')

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'nested': {
                        'path': 'affiliation_match.names',
                        'score_mode': 'max',
                        'query': {
                            'match': {
                                'affiliation_match.names.name': {
                                    'query': 'query terms',
                                    'fuzziness': 'AUTO'
                                }
                            }
                        }
                    }
                },
                'track_total_hits': True
            })

    def test_add_filters(self):
        qb = ESQueryBuilder()
        qb.add_match_all_query()
        qb.add_filters({'key1': ['val1'], 'k2': ['value2']})

        self.assertEqual(
            qb.get_query().to_dict(), {
                'query': {
                    'bool': {
                        'filter': [{
                            'terms': {
                                'key1': ['val1']
                            }
                        }, {
                            'terms': {
                                'k2': ['value2']
                            }
                        }]
                    }
                },
                'track_total_hits': True
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
                'track_total_hits': True,
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

    def test_typeahead_query(self):
        query = typeahead.text_query('Harv')
        qb = ESQueryBuilder()
        qb.add_typeahead_query(query)

        self.assertEqual(qb.get_query().to_dict(), {
            'query': query.to_dict(),
            'sort': [
                {'_script': {
                    'type': 'number',
                    'order': 'desc',
                    'script': {'source': 'Math.floor(_score / 1000)'}
                }},
                {'names_ids.prior': {'order': 'desc', 'mode': 'max', 'nested': {'path': 'names_ids'}}},
                {'_score': {'order': 'desc'}},
                {'id': {'order': 'asc'}}
            ],
            'track_total_hits': 10000,
            '_source': {'excludes': ['names_ids', 'affiliation_match']}
        })
        self.assertIs(qb.get_query()._using, ES7_TYPEAHEAD, 'typeahead runs on the 2-second client')

    def test_paginate(self):
        qb = ESQueryBuilder()
        qb.add_match_all_query()
        qb.paginate(10)

        self.assertEqual(qb.get_query().to_dict(), {
            'query': {
                'match_all': {}
            },
            'from': 180,
            'size': 20,
            'track_total_hits': True
        })

    def test_paginate_page_size_within_result_10000(self):
        for page, page_size, start, size in [(3, 5, 10, 5), (3334, 3, 9999, 1), (2000, 5, 9995, 5)]:
            with self.subTest(page=page, page_size=page_size):
                qb = ESQueryBuilder()
                qb.add_match_all_query()
                qb.paginate(page, page_size)

                self.assertEqual(qb.get_query().to_dict(), {
                    'query': {
                        'match_all': {}
                    },
                    'from': start,
                    'size': size,
                    'track_total_hits': True
                })
