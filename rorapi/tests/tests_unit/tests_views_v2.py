import json
import mock
import os

from django.test import SimpleTestCase, Client
from rest_framework.test import APIRequestFactory

from rorapi.common import views
from rorapi.v2.models import Organization as OrganizationV2

from .utils import IterableAttrDict

factory = APIRequestFactory()

class ViewListTestCase(SimpleTestCase):

    V2_VERSION = 'v2'

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es7_v2.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations_with_affiliations_match(self, search_mock):
        # Create mock data with affiliation_match field required for single search
        mock_hit = {
            "_index": "organizations-v2",
            "_type": "_doc", 
            "_id": "https://ror.org/02en5vm52",
            "_score": 1.0,
            "_source": {
                "id": "https://ror.org/02en5vm52",
                "status": "active",
                "locations": [
                    {
                        "geonames_id": 2988507,
                        "geonames_details": {
                            "continent_code": "EU",
                            "continent_name": "Europe", 
                            "country_code": "FR",
                            "country_name": "France",
                            "lat": 48.8566,
                            "lng": 2.3522,
                            "name": "Paris"
                        }
                    }
                ],
                "names": [
                    {
                        "value": "Sorbonne University",
                        "types": ["ror_display", "label"],
                        "lang": "fr"
                    }
                ],
                "affiliation_match": {
                    "names": [
                        {"name": "Sorbonne University"},
                        {"name": "Sorbonne Université"},
                        {"name": "Université de la Sorbonne"}
                    ]
                },
                "types": ["Education"],
                "established": 2018
            }
        }
        
        mock_response = IterableAttrDict(
            {"hits": {"hits": [mock_hit], "total": {"value": 1}}},
            [mock_hit]
        )
        search_mock.return_value = mock_response
        
        view = views.OrganizationViewSet.as_view({'get': 'list'})
        data = {'affiliation':'Sorbonne University, France',
                'single_search': ''}
        request = factory.get('/v2/organizations', data)

        response = view(request, version=self.V2_VERSION)
        response.render()
        organizations = json.loads(response.content.decode('utf-8'))

        print("testing affiliations match: ", organizations)
        self.assertEqual(response.status_code, 200)
        self.assertIn('items', organizations)
        self.assertGreater(len(organizations['items']), 0)


    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/v2/organizations')
        response = view(request, version=self.V2_VERSION)
        response.render()
        organizations = json.loads(response.content.decode('utf-8'))

        search_mock.assert_called_once()

        self.assertEquals(organizations['number_of_results'],
                          self.test_data['hits']['total']['value'])
        self.assertEquals(organizations['time_taken'], self.test_data['took'])
        self.assertEquals(
            len(organizations['meta']['types']),
            len(self.test_data['aggregations']['types']['buckets']))
        for ret, exp in \
                zip(organizations['meta']['types'],
                    self.test_data['aggregations']['types']['buckets']):
            self.assertEquals(ret['title'], exp['key'])
            self.assertEquals(ret['count'], exp['doc_count'])
        self.assertEquals(
            len(organizations['meta']['countries']),
            len(self.test_data['aggregations']['countries']['buckets']))
        for ret, exp in \
                zip(organizations['meta']['countries'],
                    self.test_data['aggregations']['countries']['buckets']):
            self.assertEquals(ret['id'], exp['key'].lower())
            self.assertEquals(ret['count'], exp['doc_count'])
        self.assertEquals(
            len(organizations['meta']['continents']),
            len(self.test_data['aggregations']['continents']['buckets']))
        for ret, exp in \
                zip(organizations['meta']['continents'],
                    self.test_data['aggregations']['continents']['buckets']):
            self.assertEquals(ret['id'], exp['key'].lower())
            self.assertEquals(ret['count'], exp['doc_count'])

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_invalid_search_organizations(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/v2/organizations?query=query&illegal=whatever&' +
                              'filter=fi1:e,types:F,f3,field2:44&another=3&' +
                              'page=third')
        response = view(request, version=self.V2_VERSION)
        response.render()
        organizations = json.loads(response.content.decode('utf-8'))

        self.assertEquals(list(organizations.keys()), ['errors'])
        self.assertEquals(len(organizations['errors']), 6)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_query_redirect(self, search_mock):
        client = Client()
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        response = client.get('/v2/organizations?query.names=query')
        self.assertRedirects(response, '/v2/organizations?query=query')

class ViewRetrievalTestCase(SimpleTestCase):

    V2_VERSION = 'v2'

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_retrieve_es7_v2.json'), 'r') as f:
            self.test_data = json.load(f)
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es7.json'), 'r') as f:
            self.test_data_empty = json.load(f)

        self.maxDiff = None

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/v2/organizations/https://ror.org/02atag894')
        response = view(request, pk='https://ror.org/02atag894', version=self.V2_VERSION)
        response.render()
        organization = json.loads(response.content.decode('utf-8'))
        # go through every attribute and check to see that they are equal
        self.assertEquals(response.status_code, 200)
        self.assertEquals(organization['admin'], self.test_data['hits']['hits'][0]['_source']['admin'])
        for d in organization['domains']:
            self.assertIn(d, self.test_data['hits']['hits'][0]['_source']['domains'])
        self.assertEquals(organization['established'], self.test_data['hits']['hits'][0]['_source']['established'])
        for e in organization['external_ids']:
            self.assertIn(e, self.test_data['hits']['hits'][0]['_source']['external_ids'])
        self.assertEquals(organization['id'], self.test_data['hits']['hits'][0]['_source']['id'])
        for l in organization['links']:
            self.assertIn(l, self.test_data['hits']['hits'][0]['_source']['links'])
        for l in organization['locations']:
            self.assertIn(l, self.test_data['hits']['hits'][0]['_source']['locations'])
        for n in organization['names']:
            self.assertIn(n, self.test_data['hits']['hits'][0]['_source']['names'])
        for r in organization['relationships']:
            self.assertIn(r, self.test_data['hits']['hits'][0]['_source']['relationships'])
        self.assertEquals(organization['status'], self.test_data['hits']['hits'][0]['_source']['status'])
        for t in organization['types']:
            self.assertIn(t, self.test_data['hits']['hits'][0]['_source']['types'])


    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_non_existing_organization(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/v2/organizations/https://ror.org/052gg0110')
        response = view(request, pk='https://ror.org/052gg0110', version=self.V2_VERSION)
        response.render()
        organization = json.loads(response.content.decode('utf-8'))

        self.assertEquals(response.status_code, 404)
        self.assertEquals(list(organization.keys()), ['errors'])
        self.assertEquals(len(organization['errors']), 1)
        self.assertTrue(any(['does not exist' in e for e in organization['errors']]))

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_invalid_id(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/v2/organizations/https://ror.org/abc123')
        response = view(request, pk='https://ror.org/abc123', version=self.V2_VERSION)
        response.render()
        organization = json.loads(response.content.decode('utf-8'))

        self.assertEquals(response.status_code, 404)
        self.assertEquals(list(organization.keys()), ['errors'])
        self.assertEquals(len(organization['errors']), 1)
        self.assertTrue(any(['not a valid' in e for e in organization['errors']]))


class GenerateIdViewTestCase(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es7.json'), 'r') as f:
            self.test_data_empty = json.load(f)
        self.maxDiff = None

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_generateid_success(self, search_mock, permission_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])
        permission_mock.return_value = True
        response = self.client.get('/generateid')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/generateid')
        self.assertEquals(response.status_code, 403)


class GenerateIdViewTestCase(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es7.json'), 'r') as f:
            self.test_data_empty = json.load(f)
        self.maxDiff = None

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_generateid_success(self, search_mock, permission_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])
        permission_mock.return_value = True
        response = self.client.get('/generateid')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/generateid')
        self.assertEquals(response.status_code, 403)


class GenerateAddressViewTestCase(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_address.json'), 'r') as f:
            self.test_data_address = json.load(f)
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_address_empty.json'), 'r') as f:
            self.test_data_address_empty = json.load(f)
        self.maxDiff = None

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('update_address.new_geonames_v2')
    def test_generateaddress_success(self, address_mock, permission_mock):
        address_mock.return_value = self.test_data_address
        permission_mock.return_value = True
        response = self.client.get('/generateaddress/5378538')
        self.assertContains(response, 'address')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('update_address.new_geonames_v2')
    def test_generateaddress_fail_empty(self, address_mock, permission_mock):
        address_mock.return_value = self.test_data_address_empty
        permission_mock.return_value = True
        response = self.client.get('/v2/generateaddress/0000000')
        self.assertContains(response, 'Expecting value')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/v2/generateaddress/5378538')
        self.assertEquals(response.status_code, 403)

class IndexRorViewTestCase(SimpleTestCase):
    def setUp(self):
        self.success_msg = {"status": "OK", "msg": "dir indexed"}
        self.error_msg = {"status": "ERROR", "msg": "error"}
        self.maxDiff = None

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.common.views.process_files')
    def test_index_ror_success(self, index_mock, permission_mock):
        index_mock.return_value = self.success_msg
        permission_mock.return_value = True
        response = self.client.get('/v2/indexdata/foo')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.common.views.process_files')
    def test_index_ror_fail_error(self, index_mock, permission_mock):
        index_mock.return_value = self.error_msg
        permission_mock.return_value = True
        response = self.client.get('/v2/indexdata/foo')
        self.assertEquals(response.status_code, 400)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_index_ror_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/v2/indexdata/foo')
        self.assertEquals(response.status_code, 403)

class HeartbeatViewTestCase(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es7_v2.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_heartbeat_success(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        response = self.client.get('/v2/heartbeat')
        self.assertEquals(response.status_code, 200)

class BulkUpdateViewTestCase(SimpleTestCase):
    def setUp(self):
        self.csv_errors_empty = []
        self.csv_errors_error = ['error']
        self.process_csv_msg = {"filename":"filename.zip", "rows processed":1,"created":0,"udpated":0,"skipped":1}
        self.maxDiff = None

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.common.views.validate_csv')
    @mock.patch('rorapi.common.views.process_csv')
    def test_bulkupdate_success(self, process_csv_mock, validate_csv_mock, permission_mock):

        permission_mock.return_value = True
        validate_csv_mock.return_value = self.csv_errors_empty
        process_csv_mock.return_value = None, self.process_csv_msg
        with open(os.path.join(os.path.dirname(__file__),
                             'data/test_upload_csv.csv'), 'rb') as f:
            response = self.client.post('/v2/bulkupdate', {"file":f})
        self.assertEquals(response.status_code, 201)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.common.views.validate_csv')
    def test_bulkupdate_fail_error(self, validate_csv_mock, permission_mock):
        permission_mock.return_value = True
        validate_csv_mock.return_value = self.csv_errors_error
        response = self.client.post('/v2/bulkupdate')
        self.assertEquals(response.status_code, 400)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_bulkupdate_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.post('/v2/bulkupdate')
        self.assertEquals(response.status_code, 403)

class CreateOrganizationViewTestCase(SimpleTestCase):
    # TODO: complete tests. For now just test that endpoint can't be accessed without creds.
    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_create_record_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.post('/v2/organizations')
        self.assertEquals(response.status_code, 403)

class UpdateOrganizationViewTestCase(SimpleTestCase):
    # TODO: complete tests. For now just test that endpoint can't be accessed without creds.
    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_create_record_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.put('/v2/organizations/foo')
        self.assertEquals(response.status_code, 403)

class IndexRorDumpViewTestCase(SimpleTestCase):
    def setUp(self):
        self.success_msg = "SUCCESS: ROR dataset vX.XX-XXXX-XX-XX-ror-data indexed in version X. Using test repo: X"
        self.error_msg = "ERROR: ROR dataset for file vX.XX-XXXX-XX-XX-ror-data not found. Please generate the data dump first."
        self.maxDiff = None

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('django.core.management.call_command')
    def test_index_ror_success(self, index_mock, permission_mock):
        index_mock.return_value = self.success_msg
        permission_mock.return_value = True
        response = self.client.get('/v2/indexdatadump/v1.1-1111-11-11-ror-data/prod')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('django.core.management.call_command')
    def test_index_ror_fail_error(self, index_mock, permission_mock):
        index_mock.return_value = self.error_msg
        permission_mock.return_value = True
        response = self.client.get('/v2/indexdatadump/v1.1-1111-11-11-ror-data/prod')
        self.assertEquals(response.status_code, 400)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_index_ror_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/v2/indexdatadump/v1.1-1111-11-11-ror-data/prod')
        self.assertEquals(response.status_code, 403)