from django.test import SimpleTestCase

from ..models_v1 import Entity, ExternalIds, OrganizationV1, TypeBucket, \
    CountryBucket, Aggregations, ErrorsV1, MatchedOrganization, MatchingResultV1
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


class ExternalIdsTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = {
            'ISNI': {
                'preferred': 'isni-p',
                'all': ['isni-a', 'isni-b']
            },
            'GRID': {
                'preferred': 'grid-p',
                'all': 'grid-a'
            }
        }
        entity = ExternalIds(AttrDict(data))
        self.assertEqual(entity.ISNI.preferred, data['ISNI']['preferred'])
        self.assertEqual(entity.ISNI.all, data['ISNI']['all'])
        self.assertEqual(entity.GRID.preferred, data['GRID']['preferred'])
        self.assertEqual(entity.GRID.all, data['GRID']['all'])

    def test_omit_attributes(self):
        entity = ExternalIds(
            AttrDict({
                'FundRef': {
                    'preferred': 'fr-p',
                    'all': ['fr-a', 'fr-b']
                },
                'GRID': {
                    'preferred': 'grid-p',
                    'all': 'grid-a'
                },
                'other': {
                    'preferred': 'isni-p',
                    'all': ['isni-a', 'isni-b']
                }
            }))
        msg = '\'ExternalIds\' object has no attribute \'{}\''
        with self.assertRaisesMessage(AttributeError, msg.format('ISNI')):
            entity.ISNI
        with self.assertRaisesMessage(AttributeError, msg.format('HESA')):
            entity.HESA
        with self.assertRaisesMessage(AttributeError, msg.format('other')):
            entity.other


class OrganizationTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = \
            {'id': 'ror-id',
             'name': 'University of Gallifrey',
             'types': ['school', 'research centre'],
             'links': [],
             'ip_addresses': [],
             'email_address':None,
             'aliases': ['Gallifrey University',
                         'Timey-Wimey University of Gallifrey'],
             'acronyms': ['UG'],
             'addresses': [
                {"lat": "49.198027","lng": "-123.007714","state_code": "CA-BC","city": "Burnaby","primary":False,"geonames_city": {"id": 5911606,"city": "Burnaby","geonames_admin1": {"name": "British Columbia","id": "5909050","ascii_name": "British Columbia","code": "CA.02"},
                "geonames_admin2": {"name": "Metro Vancouver Regional District","id": "5965814","ascii_name": "Metro Vancouver Regional District","code": "CA.02.5915"},"nuts_level1": {"name": "SLOVENIJA","code": "SI0"},"nuts_level2": {"name": "Vzhodna Slovenija","code": "SI03"},"nuts_level3": {"name": "TEST","code": "SI036"}},"postcode": "123456","line": "123 Somewhere Over A Rainbow","country_geonames_id": 6251999, "state":"British Columbia"}],
             'relationships': [
                 {'label': 'Calvary Hospital', 'type': 'Related', 'id':'grid.1234.6'}],
             'established': 1946,
             'status': 'active',
             'wikipedia_url': 'https://en.wikipedia.org/wiki/Gallifrey',
             'labels': [
                 {'label': 'Uniwersytet Gallifrenski', 'iso639': 'pl'},
                 {'label': 'ben DuSaQ\'a\'Daq DawI\' SoH gallifrey',
                  'iso639': 'kl'}],
             'country': {'country_name': 'Gallifrey', 'country_code': 'GE'},
             'external_ids': {
                 'ISNI': {'preferred': '0000 0004', 'all': ['0000 0004']},
                 'FundRef': {'preferred': None, 'all': ['5011004567542']},
                 'GRID': {'preferred': 'grid.12580.34',
                          'all': 'grid.12580.34'}}}
        organization = OrganizationV1(AttrDict(data))
        self.assertEqual(organization.id, data['id'])
        self.assertEqual(organization.name, data['name'])
        self.assertEqual(organization.types, data['types'])
        self.assertEqual(organization.established, data['established'])
        self.assertEqual(organization.addresses[0].lat,
                         data['addresses'][0]['lat'])
        self.assertEqual(organization.addresses[0].lng,
                         data['addresses'][0]['lng'])
        self.assertEqual(organization.addresses[0].state_code,
                         data['addresses'][0]['state_code'])
        self.assertEqual(organization.addresses[0].city,
                         data['addresses'][0]['city'])
        self.assertEqual(organization.addresses[0].geonames_city.id,
                         data['addresses'][0]['geonames_city']['id'])
        self.assertEqual(organization.addresses[0].postcode,
                         data['addresses'][0]['postcode'])
        self.assertEqual(organization.addresses[0].line,
                         data['addresses'][0]['line'])
        self.assertEqual(organization.addresses[0].country_geonames_id,
                         data['addresses'][0]['country_geonames_id'])
        self.assertEqual(organization.links, data['links'])
        self.assertEqual(organization.aliases, data['aliases'])
        self.assertEqual(organization.acronyms, data['acronyms'])
        self.assertEqual(organization.status, data['status'])
        self.assertEqual(organization.wikipedia_url, data['wikipedia_url'])
        self.assertEqual(len(organization.labels), 2)
        self.assertEqual(organization.labels[0].label,
                         data['labels'][0]['label'])
        self.assertEqual(organization.labels[0].iso639,
                         data['labels'][0]['iso639'])
        self.assertEqual(organization.labels[1].label,
                         data['labels'][1]['label'])
        self.assertEqual(organization.labels[1].iso639,
                         data['labels'][1]['iso639'])
        self.assertEqual(organization.country.country_name,
                         data['country']['country_name'])
        self.assertEqual(organization.country.country_code,
                         data['country']['country_code'])
        self.assertEqual(organization.external_ids.ISNI.preferred,
                         data['external_ids']['ISNI']['preferred'])
        self.assertEqual(organization.external_ids.ISNI.all,
                         data['external_ids']['ISNI']['all'])
        self.assertEqual(organization.external_ids.FundRef.preferred,
                         data['external_ids']['FundRef']['preferred'])
        self.assertEqual(organization.external_ids.FundRef.all,
                         data['external_ids']['FundRef']['all'])
        self.assertEqual(organization.external_ids.GRID.preferred,
                         data['external_ids']['GRID']['preferred'])
        self.assertEqual(organization.external_ids.GRID.all,
                         data['external_ids']['GRID']['all'])


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
             {'id': 'ror-id',
              'name': 'University of Gallifrey',
              'types': ['research centre'],
              'links': [],
              'aliases': [],
              'acronyms': [],
              'wikipedia_url': 'https://en.wikipedia.org/wiki/Gallifrey',
              'labels': [],
              'country': {'country_name': 'Gallifrey', 'country_code': 'GE'},
              'external_ids': {},
              'status': 'active',
              'established': 1979,
              'relationships': [],
              'addresses': [],
              'ip_addresses': []}}
        organization = MatchedOrganization(AttrDict(data))
        self.assertEqual(organization.substring, data['substring'])
        self.assertEqual(organization.score, data['score'])
        self.assertEqual(organization.matching_type, data['matching_type'])
        self.assertEqual(organization.chosen, data['chosen'])
        self.assertEqual(organization.organization.id,
                         data['organization']['id'])
        self.assertEqual(organization.organization.name,
                         data['organization']['name'])


class ErrorsTestCase(SimpleTestCase):
    def test_attributes_exist(self):
        data = ['err1', 'e2', 'terrible error 3']
        error = ErrorsV1(data)
        self.assertEqual(error.errors, data)
