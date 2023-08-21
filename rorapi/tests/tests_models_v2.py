from django.test import SimpleTestCase

from ..models_v2 import Entity, OrganizationV2, TypeBucket, \
    CountryBucket, Aggregations, ErrorsV2, MatchedOrganization, MatchingResultV2
from .utils import AttrDict


class EntityTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = {'a': 0, 'b': 123, 'third': 'a thousand'}
        entity = Entity(AttrDict(data), ['a', 'third', 'b'])
        self.assertEqual(entity.a, data['a'])
        self.assertEqual(entity.b, data['b'])
        self.assertEqual(entity.third, data['third'])

    def test_omits_attributes(self):
        data = {'a': 0, 'b': 123, 'third': 'a thousand'}
        entity = Entity(AttrDict(data), ['a'])
        self.assertEqual(entity.a, data['a'])
        msg = '\'Entity\' object has no attribute \'{}\''
        with self.assertRaisesMessage(AttributeError, msg.format('b')):
            entity.b
        with self.assertRaisesMessage(AttributeError, msg.format('third')):
            entity.third


class OrganizationTestCase(SimpleTestCase):
    maxDiff = None

    def test_attributes_exist(self):
        data = \
            {
                "admin":{
                    "created":{
                        "date":"2019-05-13",
                        "schema_version":"1.0"
                    },
                    "last_modified":{
                        "date":"2023-08-17",
                        "schema_version":"2.0"
                    }
                },
                "domains":[

                ],
                "established":1946,
                "external_ids":[
                    {
                        "type":"isni",
                        "all":[
                            "0000 0004"
                        ],
                        "preferred":"0000 0004"
                    },
                    {
                        "type":"fundref",
                        "all":[
                            "5011004567542"
                        ],
                        "preferred":"None"
                    },
                    {
                        "type":"grid",
                        "all":[
                            "grid.12580.34"
                        ],
                        "preferred":"grid.12580.34"
                    }
                ],
                "id":"ror-id",
                "links":[

                ],
                "locations":[
                    {
                        "geonames_id":5911606,
                        "geonames_details":{
                            "lat":"49.198027",
                            "lng":"-123.007714",
                            "name":"Burnaby",
                            "country_name":"Gallifrey",
                            "country_code":"GE"
                        }
                    }
                ],
                "names":[
                    {
                        "types":[
                            "label",
                            "ror_display"
                        ],
                        "value":"University of Gallifrey",
                        "lang":"None"
                    },
                    {
                        "types":[
                            "alias"
                        ],
                        "value":"Gallifrey University",
                        "lang":"None"
                    },
                    {
                        "types":[
                            "alias"
                        ],
                        "value":"Timey-Wimey University of Gallifrey",
                        "lang":"None"
                    },
                    {
                        "types":[
                            "acronym"
                        ],
                        "value":"UG",
                        "lang":"None"
                    },
                    {
                        "types":[
                            "label"
                        ],
                        "value":"Uniwersytet Gallifrenski",
                        "lang":"pl"
                    },
                    {
                        "types":[
                            "label"
                        ],
                        "value":"ben DuSaQ\\'a\\'Daq DawI\\' SoH gallifrey",
                        "lang":"kl"
                    }
                ],
                "relationships":[
                    {
                        "label":"Calvary Hospital",
                        "type":"Related",
                        "id":"grid.1234.6"
                    }
                ],
                "status":"active",
                "types":[
                    "school",
                    "research centre"
                ]
            }

        organization = OrganizationV2(AttrDict(data))
        self.assertEqual(organization.id, data['id'])
        self.assertEqual(organization.types, data['types'])
        self.assertEqual(organization.established, data['established'])
        self.assertEqual(organization.locations[0].geonames_details.lat,
                         data['locations'][0]['geonames_details']['lat'])
        self.assertEqual(organization.locations[0].geonames_details.lng,
                         data['locations'][0]['geonames_details']['lng'])
        self.assertEqual(organization.locations[0].geonames_details.country_code,
                         data['locations'][0]['geonames_details']['country_code'])
        self.assertEqual(organization.locations[0].geonames_details.country_name,
                         data['locations'][0]['geonames_details']['country_name'])
        self.assertEqual(organization.locations[0].geonames_details.name,
                         data['locations'][0]['geonames_details']['name'])
        self.assertEqual(organization.locations[0].geonames_id,
                         data['locations'][0]['geonames_id'])

        self.assertEqual(organization.links, data['links'])
        self.assertEqual(organization.status, data['status'])

        self.assertEqual(len(organization.names), 6)

        for i, name in enumerate(organization.names):
            self.assertEqual(organization.names[i].value,
                         data['names'][i]['value'])
            self.assertEqual(organization.names[i].types,
                         data['names'][i]['types'])
            self.assertEqual(organization.names[i].lang,
                         data['names'][i]['lang'])

        for i, ext_id in enumerate(organization.external_ids):
            self.assertEqual(organization.external_ids[i].all,
                         data['external_ids'][i]['all'])
            self.assertEqual(organization.external_ids[i].preferred,
                         data['external_ids'][i]['preferred'])
            self.assertEqual(organization.external_ids[i].type,
                         data['external_ids'][i]['type'])


class TypeBucketTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        bucket = TypeBucket(AttrDict({'key': 'Type', 'doc_count': 482}))
        self.assertEqual(bucket.id, 'type')
        self.assertEqual(bucket.title, 'Type')
        self.assertEqual(bucket.count, 482)


class CountryBucketTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        bucket = CountryBucket(AttrDict({'key': 'IE', 'doc_count': 4821}))
        self.assertEqual(bucket.id, 'ie')
        self.assertEqual(bucket.title, 'Ireland')
        self.assertEqual(bucket.count, 4821)


class AggregationsTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        aggr = Aggregations(
            AttrDict({
                'types': {
                    'buckets': [{
                        'key': 'TyPE 1',
                        'doc_count': 482
                    }, {
                        'key': 'Type2',
                        'doc_count': 42
                    }]
                },
                'countries': {
                    'buckets': [{
                        'key': 'IE',
                        'doc_count': 48212
                    }, {
                        'key': 'FR',
                        'doc_count': 4821
                    }, {
                        'key': 'GB',
                        'doc_count': 482
                    }, {
                        'key': 'US',
                        'doc_count': 48
                    }]
                },
                'statuses': {
                    'buckets': [{
                        'key': 'active',
                        'doc_count': 102927
                    }, {
                        'key': 'inactive',
                        'doc_count': 3
                    }, {
                        'key': 'withdrawn',
                        'doc_count': 2
                    }]
                }
            }))
        self.assertEqual(len(aggr.types), 2)
        self.assertEqual(aggr.types[0].id, 'type 1')
        self.assertEqual(aggr.types[0].title, 'TyPE 1')
        self.assertEqual(aggr.types[0].count, 482)
        self.assertEqual(aggr.types[1].id, 'type2')
        self.assertEqual(aggr.types[1].title, 'Type2')
        self.assertEqual(aggr.types[1].count, 42)
        self.assertEqual(len(aggr.countries), 4)
        self.assertEqual(aggr.countries[0].id, 'ie')
        self.assertEqual(aggr.countries[0].title, 'Ireland')
        self.assertEqual(aggr.countries[0].count, 48212)
        self.assertEqual(aggr.countries[1].id, 'fr')
        self.assertEqual(aggr.countries[1].title, 'France')
        self.assertEqual(aggr.countries[1].count, 4821)
        self.assertEqual(aggr.countries[2].id, 'gb')
        self.assertEqual(
            aggr.countries[2].title,
            'United Kingdom')
        self.assertEqual(aggr.countries[2].count, 482)
        self.assertEqual(aggr.countries[3].id, 'us')
        self.assertEqual(aggr.countries[3].title, 'United States')
        self.assertEqual(aggr.countries[3].count, 48)
        self.assertEqual(aggr.statuses[0].id, 'active')
        self.assertEqual(aggr.statuses[0].title, 'active')
        self.assertEqual(aggr.statuses[0].count, 102927)
        self.assertEqual(aggr.statuses[1].id, 'inactive')
        self.assertEqual(aggr.statuses[1].title, 'inactive')
        self.assertEqual(aggr.statuses[1].count, 3)
        self.assertEqual(aggr.statuses[2].id, 'withdrawn')
        self.assertEqual(aggr.statuses[2].title, 'withdrawn')
        self.assertEqual(aggr.statuses[2].count, 2)


class MatchedOrganizationTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = \
            {'substring': 'UGallifrey',
             'score': 0.95,
             'matching_type': 'fuzzy',
             'chosen': True,
             'organization':
             {"admin":{
                    "created":{
                        "date":"2019-05-13",
                        "schema_version":"1.0"
                    },
                    "last_modified":{
                        "date":"2023-08-17",
                        "schema_version":"2.0"
                    }
                },
                'domains':[],
                'established': 1979,
                'external_ids': [],
                'id': 'ror-id',
                'links': [],
                'locations': [],
                "names":[
                    {
                        "types":[
                            "label",
                            "ror_display"
                        ],
                        "value":"University of Gallifrey",
                        "lang":"None"
                    }],
                'relationships': [],
                'status': 'active',
                'types': ['research centre']
              }}
        organization = MatchedOrganization(AttrDict(data))
        self.assertEqual(organization.substring, data['substring'])
        self.assertEqual(organization.score, data['score'])
        self.assertEqual(organization.matching_type, data['matching_type'])
        self.assertEqual(organization.chosen, data['chosen'])
        self.assertEqual(organization.organization.id,
                         data['organization']['id'])
        for i, name in enumerate(organization.organization.names):
            self.assertEqual(organization.organization.names[i].value,
                         data['organization']['names'][i]['value'])
            self.assertEqual(organization.organization.names[i].types,
                         data['organization']['names'][i]['types'])
            self.assertEqual(organization.organization.names[i].lang,
                         data['organization']['names'][i]['lang'])


class ErrorsTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = ['err1', 'e2', 'terrible error 3']
        error = ErrorsV2(data)
        self.assertEqual(error.errors, data)
