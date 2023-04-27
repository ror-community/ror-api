import json
import mock
import os

from django.test import SimpleTestCase, Client
from rest_framework.test import APIRequestFactory

from .. import views

from .utils import IterableAttrDict

factory = APIRequestFactory()

class ViewListTestCaseEs6(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es6.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        feature_mock.return_value = False

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/organizations')
        response = view(request)
        response.render()
        organizations = json.loads(response.content.decode('utf-8'))

        search_mock.assert_called_once()

        self.assertEquals(organizations['number_of_results'],
                          self.test_data['hits']['total'])
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

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_invalid_search_organizations(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        feature_mock.return_value = False

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/organizations?query=query&illegal=whatever&' +
                              'filter=fi1:e,types:F,f3,field2:44&another=3&' +
                              'page=third')
        response = view(request)
        response.render()
        organizations = json.loads(response.content.decode('utf-8'))

        self.assertEquals(list(organizations.keys()), ['errors'])
        self.assertEquals(len(organizations['errors']), 6)

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_query_redirect(self, search_mock, feature_mock):
        client = Client()
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        feature_mock.return_value = False

        response = client.get('/organizations?query.name=query')
        self.assertRedirects(response, '/organizations?query=query')

        response = client.get('/organizations?query.names=query')
        self.assertRedirects(response, '/organizations?query=query')

class ViewListTestCaseEs7(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es7.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_search_organizations(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        feature_mock.return_value = True

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/organizations')
        response = view(request)
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

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_invalid_search_organizations(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        feature_mock.return_value = True

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/organizations?query=query&illegal=whatever&' +
                              'filter=fi1:e,types:F,f3,field2:44&another=3&' +
                              'page=third')
        response = view(request)
        response.render()
        organizations = json.loads(response.content.decode('utf-8'))

        self.assertEquals(list(organizations.keys()), ['errors'])
        self.assertEquals(len(organizations['errors']), 6)

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_query_redirect(self, search_mock, feature_mock):
        client = Client()
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        feature_mock.return_value = True

        response = client.get('/organizations?query.name=query')
        self.assertRedirects(response, '/organizations?query=query')

        response = client.get('/organizations?query.names=query')
        self.assertRedirects(response, '/organizations?query=query')

class ViewRetrievalTestCaseEs6(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_retrieve_es6.json'), 'r') as f:
            self.test_data = json.load(f)
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es6.json'), 'r') as f:
            self.test_data_empty = json.load(f)

        self.maxDiff = None

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_organization(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        feature_mock.return_value = False

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/organizations/https://ror.org/02atag894')
        response = view(request, pk='https://ror.org/02atag894')
        response.render()
        organization = json.loads(response.content.decode('utf-8'))
        # go through every attribute and check to see that they are equal
        self.assertEquals(response.status_code, 200)
        self.assertEquals(organization, self.test_data['hits']['hits'][0])

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_non_existing_organization(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])
        feature_mock.return_value = False

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/organizations/https://ror.org/052gg0110')
        response = view(request, pk='https://ror.org/052gg0110')
        response.render()
        organization = json.loads(response.content.decode('utf-8'))

        self.assertEquals(response.status_code, 404)
        self.assertEquals(list(organization.keys()), ['errors'])
        self.assertEquals(len(organization['errors']), 1)
        self.assertTrue(any(['does not exist' in e for e in organization['errors']]))

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_invalid_id(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])
        feature_mock.return_value = False

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/organizations/https://ror.org/abc123')
        response = view(request, pk='https://ror.org/abc123')
        response.render()
        organization = json.loads(response.content.decode('utf-8'))

        self.assertEquals(response.status_code, 404)
        self.assertEquals(list(organization.keys()), ['errors'])
        self.assertEquals(len(organization['errors']), 1)
        self.assertTrue(any(['not a valid' in e for e in organization['errors']]))

class ViewRetrievalTestCaseEs7(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_retrieve_es7.json'), 'r') as f:
            self.test_data = json.load(f)
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es7.json'), 'r') as f:
            self.test_data_empty = json.load(f)

        self.maxDiff = None

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_organization(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        feature_mock.return_value = True

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/organizations/https://ror.org/02atag894')
        response = view(request, pk='https://ror.org/02atag894')
        response.render()
        organization = json.loads(response.content.decode('utf-8'))
        # go through every attribute and check to see that they are equal
        self.assertEquals(response.status_code, 200)
        self.assertEquals(organization, self.test_data['hits']['hits'][0]['_source'])

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_non_existing_organization(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])
        feature_mock.return_value = True

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/organizations/https://ror.org/052gg0110')
        response = view(request, pk='https://ror.org/052gg0110')
        response.render()
        organization = json.loads(response.content.decode('utf-8'))

        self.assertEquals(response.status_code, 404)
        self.assertEquals(list(organization.keys()), ['errors'])
        self.assertEquals(len(organization['errors']), 1)
        self.assertTrue(any(['does not exist' in e for e in organization['errors']]))

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_invalid_id(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])
        feature_mock.return_value = True

        view = views.OrganizationViewSet.as_view({'get': 'retrieve'})
        request = factory.get('/organizations/https://ror.org/abc123')
        response = view(request, pk='https://ror.org/abc123')
        response.render()
        organization = json.loads(response.content.decode('utf-8'))

        self.assertEquals(response.status_code, 404)
        self.assertEquals(list(organization.keys()), ['errors'])
        self.assertEquals(len(organization['errors']), 1)
        self.assertTrue(any(['not a valid' in e for e in organization['errors']]))

class GenerateIdViewTestCaseEs7(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es7.json'), 'r') as f:
            self.test_data_empty = json.load(f)
        self.maxDiff = None

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_generateid_success(self, search_mock, permission_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])
        permission_mock.return_value = True
        feature_mock.return_value = True
        response = self.client.get('/generateid')
        self.assertEquals(response.status_code, 200)

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock, feature_mock):
        permission_mock.return_value = False
        feature_mock.return_value = True
        response = self.client.get('/generateid')
        self.assertEquals(response.status_code, 403)

class GenerateIdViewTestCaseEs6(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_empty_es6.json'), 'r') as f:
            self.test_data_empty = json.load(f)
        self.maxDiff = None

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_generateid_success(self, search_mock, permission_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data_empty,
                             self.test_data_empty['hits']['hits'])
        permission_mock.return_value = True
        feature_mock.return_value = False
        response = self.client.get('/generateid')
        self.assertEquals(response.status_code, 200)

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock, feature_mock):
        permission_mock.return_value = False
        feature_mock.return_value = False
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

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    @mock.patch('update_address.new_geonames')
    def test_generateaddress_success(self, address_mock, permission_mock):
        address_mock.return_value = self.test_data_address
        permission_mock.return_value = True
        response = self.client.get('/generateaddress/5378538')
        self.assertContains(response, 'address')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    @mock.patch('update_address.new_geonames')
    def test_generateaddress_fail_empty(self, address_mock, permission_mock):
        address_mock.return_value = self.test_data_address_empty
        permission_mock.return_value = True
        response = self.client.get('/generateaddress/0000000')
        self.assertContains(response, 'Expecting value')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/generateaddress/5378538')
        self.assertEquals(response.status_code, 403)

class IndexRorViewTestCaseEs6(SimpleTestCase):
    def setUp(self):
        self.success_msg = {"status": "OK", "msg": "dir indexed"}
        self.error_msg = {"status": "ERROR", "msg": "error"}
        self.maxDiff = None

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.views.process_files')
    def test_index_ror_success(self, index_mock, permission_mock):
        index_mock.return_value = self.success_msg
        permission_mock.return_value = True
        response = self.client.get('/indexdata/foo/6')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.views.process_files')
    def test_index_ror_fail_error(self, index_mock, permission_mock):
        index_mock.return_value = self.error_msg
        permission_mock.return_value = True
        response = self.client.get('/indexdata/foo/6')
        self.assertEquals(response.status_code, 400)

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    def test_index_ror_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/indexdata/foo/6')
        self.assertEquals(response.status_code, 403)

class IndexRorViewTestCaseEs7(SimpleTestCase):
    def setUp(self):
        self.success_msg = {"status": "OK", "msg": "dir indexed"}
        self.error_msg = {"status": "ERROR", "msg": "error"}
        self.maxDiff = None

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.views.process_files')
    def test_index_ror_success(self, index_mock, permission_mock):
        index_mock.return_value = self.success_msg
        permission_mock.return_value = True
        response = self.client.get('/indexdata/foo/7')
        self.assertEquals(response.status_code, 200)

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.views.process_files')
    def test_index_ror_fail_error(self, index_mock, permission_mock):
        index_mock.return_value = self.error_msg
        permission_mock.return_value = True
        response = self.client.get('/indexdata/foo/7')
        self.assertEquals(response.status_code, 400)

    @mock.patch('rorapi.views.OurTokenPermission.has_permission')
    def test_index_ror_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/indexdata/foo/7')
        self.assertEquals(response.status_code, 403)

class HeartbeatViewTestCaseEs6(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es6.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_generateid_success(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        feature_mock.return_value = False
        response = self.client.get('/heartbeat')
        self.assertEquals(response.status_code, 200)

class HeartbeatViewTestCaseEs7(SimpleTestCase):
    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es7.json'), 'r') as f:
            self.test_data = json.load(f)

    @mock.patch('ldclient.client.LDClient.variation')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_generateid_success(self, search_mock, feature_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])
        feature_mock.return_value = True
        response = self.client.get('/heartbeat')
        self.assertEquals(response.status_code, 200)