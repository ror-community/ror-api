import json
from unittest import mock
import os

from django.test import SimpleTestCase, Client, override_settings
from elasticsearch.exceptions import ConnectionError, ConnectionTimeout, TransportError
from elasticsearch_dsl import Search
from elasticsearch_dsl.response import Response
import requests
from rest_framework.test import APIRequestFactory

from rorapi.common import views
from rorapi.common.csv_update import update_record_from_csv
from rorapi.common.csv_utils import CSV_REQUIRED_FIELDS_ACTIONS
from rorapi.v2.models import MatchingResult as MatchingResultV2

from .utils import AttrDict, IterableAttrDict, effective_timeout

factory = APIRequestFactory()


def elasticsearch_error(status, kind, reason):
    error = {'type': kind, 'reason': reason}
    return TransportError(status, kind, {'error': dict(error, root_cause=[error]), 'status': status})

class ViewListTestCase(SimpleTestCase):

    V2_VERSION = 'v2'

    def setUp(self):
        with open(
                os.path.join(os.path.dirname(__file__),
                             'data/test_data_search_es7_v2.json'), 'r') as f:
            self.test_data = json.load(f)

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

        self.assertEqual(organizations['number_of_results'],
                          self.test_data['hits']['total']['value'])
        self.assertEqual(organizations['time_taken'], self.test_data['took'])
        self.assertEqual(
            len(organizations['meta']['types']),
            len(self.test_data['aggregations']['types']['buckets']))
        for ret, exp in \
                zip(organizations['meta']['types'],
                    self.test_data['aggregations']['types']['buckets']):
            self.assertEqual(ret['title'], exp['key'])
            self.assertEqual(ret['count'], exp['doc_count'])
        self.assertEqual(
            len(organizations['meta']['countries']),
            len(self.test_data['aggregations']['countries']['buckets']))
        for ret, exp in \
                zip(organizations['meta']['countries'],
                    self.test_data['aggregations']['countries']['buckets']):
            self.assertEqual(ret['id'], exp['key'].lower())
            self.assertEqual(ret['count'], exp['doc_count'])
        self.assertEqual(
            len(organizations['meta']['continents']),
            len(self.test_data['aggregations']['continents']['buckets']))
        for ret, exp in \
                zip(organizations['meta']['continents'],
                    self.test_data['aggregations']['continents']['buckets']):
            self.assertEqual(ret['id'], exp['key'].lower())
            self.assertEqual(ret['count'], exp['doc_count'])

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_query_items_have_no_matched_name(self, search_mock):
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/v2/organizations?query=harvard')
        response = view(request, version=self.V2_VERSION)
        response.render()
        organizations = json.loads(response.content.decode('utf-8'))

        self.assertTrue(organizations['items'])
        for item in organizations['items']:
            self.assertNotIn('matched_name', item)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_typeahead(self, search_mock):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/test_data_typeahead_es7_v2.json')) as f:
            test_data = json.load(f)
        search_mock.return_value = Response(Search(index='organizations-v2'), test_data)

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/v2/organizations?query.typeahead=harv&page_size=3')
        response = view(request, version=self.V2_VERSION)
        response.render()
        organizations = json.loads(response.content.decode('utf-8'))

        self.assertEqual(organizations['number_of_results'], 3)
        self.assertIsNone(organizations['meta'])
        self.assertEqual(
            [i['id'] for i in organizations['items']],
            [h['_id'] for h in test_data['hits']['hits']])
        self.assertEqual(
            organizations['items'][1]['matched_name'],
            {'lang': 'en', 'types': ['alias'],
             'value': 'Harvard–Smithsonian Center for Astrophysics'})
        self.assertIsNone(organizations['items'][2]['matched_name'])

    @mock.patch('elasticsearch.RequestsHttpConnection.perform_request', autospec=True)
    def test_typeahead_answers_503_after_one_attempt_for_every_elasticsearch_failure(self, perform_request):
        failures = [
            ('connection timeout', ConnectionTimeout(
                'TIMEOUT', 'Read timed out', requests.exceptions.ReadTimeout('Read timed out'))),
            ('connection error', ConnectionError(
                'N/A', 'Connection reset by peer', requests.exceptions.ConnectionError('Connection reset by peer'))),
            ('429', elasticsearch_error(429, 'es_rejected_execution_exception', 'rejected execution of search')),
            ('500', elasticsearch_error(500, 'injected_fault', 'injected fault')),
            ('502', elasticsearch_error(502, 'bad_gateway', 'upstream failed')),
            ('503', elasticsearch_error(503, 'search_phase_execution_exception', 'all shards failed')),
            ('504', elasticsearch_error(504, 'gateway_timeout', 'upstream timed out')),
        ]

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        for name, failure in failures:
            with self.subTest(failure=name):
                perform_request.reset_mock()
                perform_request.side_effect = failure

                response = view(factory.get('/v2/organizations?query.typeahead=harv'), version=self.V2_VERSION)
                response.render()
                body = json.loads(response.content.decode('utf-8'))

                self.assertEqual(response.status_code, 503)
                self.assertEqual(list(body.keys()), ['errors'])
                self.assertEqual(len(body['errors']), 1)
                self.assertIsInstance(body['errors'][0], str)
                self.assertNotEqual(body['errors'][0], '')
                self.assertEqual(perform_request.call_count, 1)
                self.assertEqual(effective_timeout(perform_request.call_args), 2)

    @mock.patch('elasticsearch.RequestsHttpConnection.perform_request', autospec=True)
    def test_other_searches_retry_and_raise_when_elasticsearch_fails(self, perform_request):
        perform_request.side_effect = elasticsearch_error(503, 'search_phase_execution_exception', 'all shards failed')

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        for url in ['/v2/organizations?query=harvard', '/v2/organizations']:
            with self.subTest(url=url):
                perform_request.reset_mock()
                with self.assertRaises(TransportError) as raised:
                    view(factory.get(url), version=self.V2_VERSION)
                self.assertEqual(raised.exception.status_code, 503)
                self.assertEqual(perform_request.call_count, 4,
                                 "one attempt and elasticsearch-py's three default retries")

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

        self.assertEqual(list(organizations.keys()), ['errors'])
        self.assertEqual(len(organizations['errors']), 6)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_query_redirect(self, search_mock):
        client = Client()
        search_mock.return_value = \
            IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

        response = client.get('/v2/organizations?query.names=query')
        self.assertRedirects(response, '/v2/organizations?query=query')


class AffiliationDefaultMatchingTestCase(SimpleTestCase):
    """Test SINGLE_SEARCH_DEFAULT and single_search/multisearch params."""
    V2_VERSION = 'v2'

    @override_settings(SINGLE_SEARCH_DEFAULT=False)
    @mock.patch('rorapi.common.views.single_search_match_organizations')
    @mock.patch('rorapi.common.views.match_organizations')
    def test_affiliation_default_uses_multisearch_when_setting_off(
            self, match_organizations_mock, single_search_mock):
        mock_result = (None, MatchingResultV2([]))
        match_organizations_mock.return_value = mock_result
        single_search_mock.return_value = mock_result

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/v2/organizations', {'affiliation': 'Harvard University'})
        response = view(request, version=self.V2_VERSION)
        response.render()

        match_organizations_mock.assert_called_once()
        single_search_mock.assert_not_called()

    @override_settings(SINGLE_SEARCH_DEFAULT=True)
    @mock.patch('rorapi.common.views.single_search_match_organizations')
    @mock.patch('rorapi.common.views.match_organizations')
    def test_affiliation_default_uses_single_search_when_setting_on(
            self, match_organizations_mock, single_search_mock):
        mock_result = (None, MatchingResultV2([]))
        match_organizations_mock.return_value = mock_result
        single_search_mock.return_value = mock_result

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get('/v2/organizations', {'affiliation': 'Harvard University'})
        response = view(request, version=self.V2_VERSION)
        response.render()

        single_search_mock.assert_called_once()
        match_organizations_mock.assert_not_called()

    @override_settings(SINGLE_SEARCH_DEFAULT=True)
    @mock.patch('rorapi.common.views.single_search_match_organizations')
    @mock.patch('rorapi.common.views.match_organizations')
    def test_affiliation_multisearch_param_overrides_setting(
            self, match_organizations_mock, single_search_mock):
        mock_result = (None, MatchingResultV2([]))
        match_organizations_mock.return_value = mock_result
        single_search_mock.return_value = mock_result

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get(
            '/v2/organizations',
            {'affiliation': 'Harvard University', 'multisearch': ''}
        )
        response = view(request, version=self.V2_VERSION)
        response.render()

        match_organizations_mock.assert_called_once()
        single_search_mock.assert_not_called()

    @override_settings(SINGLE_SEARCH_DEFAULT=False)
    @mock.patch('rorapi.common.views.single_search_match_organizations')
    @mock.patch('rorapi.common.views.match_organizations')
    def test_affiliation_single_search_param_uses_single_search(
            self, match_organizations_mock, single_search_mock):
        mock_result = (None, MatchingResultV2([]))
        match_organizations_mock.return_value = mock_result
        single_search_mock.return_value = mock_result

        view = views.OrganizationViewSet.as_view({'get': 'list'})
        request = factory.get(
            '/v2/organizations',
            {'affiliation': 'Harvard University', 'single_search': ''}
        )
        response = view(request, version=self.V2_VERSION)
        response.render()

        single_search_mock.assert_called_once()
        match_organizations_mock.assert_not_called()


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
        self.assertEqual(response.status_code, 200)
        self.assertEqual(organization['admin'], self.test_data['hits']['hits'][0]['_source']['admin'])
        for d in organization['domains']:
            self.assertIn(d, self.test_data['hits']['hits'][0]['_source']['domains'])
        self.assertEqual(organization['established'], self.test_data['hits']['hits'][0]['_source']['established'])
        for e in organization['external_ids']:
            self.assertIn(e, self.test_data['hits']['hits'][0]['_source']['external_ids'])
        self.assertEqual(organization['id'], self.test_data['hits']['hits'][0]['_source']['id'])
        for l in organization['links']:
            self.assertIn(l, self.test_data['hits']['hits'][0]['_source']['links'])
        for l in organization['locations']:
            self.assertIn(l, self.test_data['hits']['hits'][0]['_source']['locations'])
        for n in organization['names']:
            self.assertIn(n, self.test_data['hits']['hits'][0]['_source']['names'])
        for r in organization['relationships']:
            self.assertIn(r, self.test_data['hits']['hits'][0]['_source']['relationships'])
        self.assertEqual(organization['status'], self.test_data['hits']['hits'][0]['_source']['status'])
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

        self.assertEqual(response.status_code, 404)
        self.assertEqual(list(organization.keys()), ['errors'])
        self.assertEqual(len(organization['errors']), 1)
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

        self.assertEqual(response.status_code, 404)
        self.assertEqual(list(organization.keys()), ['errors'])
        self.assertEqual(len(organization['errors']), 1)
        self.assertTrue(any(['not a valid' in e for e in organization['errors']]))


class NamesOrderTestCase(SimpleTestCase):
    """Record 0324fzd89 stores the 'Nature Canada' fr label before the 'Nature Canada' en
    ror_display, so a value sort alone cannot tell the two orders apart."""

    V2_VERSION = 'v2'
    ROR_ID = 'https://ror.org/0324fzd89'

    def setUp(self):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/test_data_retrieve_names_tie_es7_v2.json')) as f:
            self.test_data = json.load(f)
        self.hit = self.test_data['hits']['hits'][0]
        self.stored_names = self.hit['_source']['names']
        self.maxDiff = None

    def display_first_names(self):
        alias, label_fr, ror_display = self.stored_names
        return [ror_display, alias, label_fr]

    def es_result(self):
        return IterableAttrDict(self.test_data, self.test_data['hits']['hits'])

    def read(self, action, path, **view_kwargs):
        view = views.OrganizationViewSet.as_view({'get': action})
        response = view(factory.get(path), version=self.V2_VERSION, **view_kwargs)
        response.render()
        return json.loads(response.content.decode('utf-8'))

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('update_address.new_geonames_v2')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_put_keeps_stored_names_order(self, search_mock, geonames_mock, permission_mock):
        search_mock.return_value = self.es_result()
        geonames_mock.return_value = {'location': self.hit['_source']['locations'][0]}
        permission_mock.return_value = True

        response = self.client.put(
            '/v2/organizations/' + self.ROR_ID,
            data=json.dumps({'id': self.ROR_ID, 'status': 'inactive'}),
            content_type='application/json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['names'], self.stored_names)

    @mock.patch('update_address.new_geonames_v2')
    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_csv_update_keeps_stored_names_order(self, search_mock, geonames_mock):
        search_mock.return_value = self.es_result()
        geonames_mock.return_value = {'location': self.hit['_source']['locations'][0]}
        row = {field: '' for field in CSV_REQUIRED_FIELDS_ACTIONS}
        row['id'] = self.ROR_ID
        row['status'] = 'replace==inactive'

        errors, record = update_record_from_csv(row, self.V2_VERSION)

        self.assertEqual(errors, [])
        self.assertEqual(record['names'], self.stored_names)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_retrieve_keeps_stored_names_order(self, search_mock):
        search_mock.return_value = self.es_result()

        organization = self.read('retrieve', '/v2/organizations/' + self.ROR_ID, pk=self.ROR_ID)

        self.assertEqual(organization['names'], self.stored_names)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_list_keeps_stored_names_order(self, search_mock):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/test_data_search_es7_v2.json')) as f:
            test_data = json.load(f)
        test_data['hits']['hits'][0]['_source'] = self.hit['_source']
        search_mock.return_value = IterableAttrDict(test_data, test_data['hits']['hits'])

        organizations = self.read('list', '/v2/organizations?query=nature')

        self.assertEqual(organizations['items'][0]['names'], self.stored_names)

    @mock.patch('elasticsearch_dsl.Search.execute')
    def test_typeahead_lists_ror_display_first(self, search_mock):
        with open(os.path.join(os.path.dirname(__file__),
                               'data/test_data_typeahead_es7_v2.json')) as f:
            test_data = json.load(f)
        test_data['hits']['hits'][0]['_source'] = self.hit['_source']
        search_mock.return_value = Response(Search(index='organizations-v2'), test_data)

        organizations = self.read('list', '/v2/organizations?query.typeahead=nature')

        self.assertEqual(organizations['items'][0]['names'], self.display_first_names())

    @mock.patch('rorapi.common.views.match_organizations')
    def test_matching_keeps_stored_names_order(self, match_organizations_mock):
        match = AttrDict({'substring': 'Nature Canada', 'score': 1.0, 'matching_type': 'EXACT',
                          'chosen': True, 'organization': self.hit})
        match_organizations_mock.return_value = (None, MatchingResultV2([match]))

        organizations = self.read('list', '/v2/organizations?affiliation=Nature%20Canada&multisearch=')

        self.assertEqual(organizations['items'][0]['organization']['names'], self.stored_names)


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
        self.assertEqual(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/generateid')
        self.assertEqual(response.status_code, 403)


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
        self.assertEqual(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/generateid')
        self.assertEqual(response.status_code, 403)


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
        self.assertEqual(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('update_address.new_geonames_v2')
    def test_generateaddress_fail_empty(self, address_mock, permission_mock):
        address_mock.return_value = self.test_data_address_empty
        permission_mock.return_value = True
        response = self.client.get('/v2/generateaddress/0000000')
        self.assertContains(response, 'Expecting value')
        self.assertEqual(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_generateid_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.get('/v2/generateaddress/5378538')
        self.assertEqual(response.status_code, 403)

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
        response = self.client.post('/v2/indexdata/foo')
        self.assertEqual(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.common.views.process_files')
    def test_index_ror_fail_error(self, index_mock, permission_mock):
        index_mock.return_value = self.error_msg
        permission_mock.return_value = True
        response = self.client.post('/v2/indexdata/foo')
        self.assertEqual(response.status_code, 400)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_index_ror_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.post('/v2/indexdata/foo')
        self.assertEqual(response.status_code, 403)

    @mock.patch.dict(os.environ, {"TOKEN": "token-value", "ROUTE_USER": "route-user"}, clear=False)
    @mock.patch('rorapi.common.views.process_files')
    def test_index_ror_fail_no_auth_headers(self, index_mock):
        index_mock.return_value = self.success_msg
        response = self.client.post('/v2/indexdata/foo')
        self.assertEqual(response.status_code, 403)

    @mock.patch.dict(os.environ, {"TOKEN": "token-value", "ROUTE_USER": "route-user"}, clear=False)
    @mock.patch('rorapi.common.views.process_files')
    def test_index_ror_success_with_auth_headers(self, index_mock):
        index_mock.return_value = self.success_msg
        response = self.client.post(
            '/v2/indexdata/foo',
            HTTP_TOKEN='token-value',
            HTTP_ROUTE_USER='route-user'
        )
        self.assertEqual(response.status_code, 200)

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
        self.assertEqual(response.status_code, 201)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('rorapi.common.views.validate_csv')
    def test_bulkupdate_fail_error(self, validate_csv_mock, permission_mock):
        permission_mock.return_value = True
        validate_csv_mock.return_value = self.csv_errors_error
        response = self.client.post('/v2/bulkupdate')
        self.assertEqual(response.status_code, 400)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_bulkupdate_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.post('/v2/bulkupdate')
        self.assertEqual(response.status_code, 403)

class CreateOrganizationViewTestCase(SimpleTestCase):
    # TODO: complete tests. For now just test that endpoint can't be accessed without creds.
    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_create_record_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.post('/v2/organizations')
        self.assertEqual(response.status_code, 403)

class UpdateOrganizationViewTestCase(SimpleTestCase):
    # TODO: complete tests. For now just test that endpoint can't be accessed without creds.
    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_create_record_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.put('/v2/organizations/foo')
        self.assertEqual(response.status_code, 403)

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
        response = self.client.post('/v2/indexdatadump/v1.1-1111-11-11-ror-data/prod')
        self.assertEqual(response.status_code, 200)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    @mock.patch('django.core.management.call_command')
    def test_index_ror_fail_error(self, index_mock, permission_mock):
        index_mock.return_value = self.error_msg
        permission_mock.return_value = True
        response = self.client.post('/v2/indexdatadump/v1.1-1111-11-11-ror-data/prod')
        self.assertEqual(response.status_code, 400)

    @mock.patch('rorapi.common.views.OurTokenPermission.has_permission')
    def test_index_ror_fail_no_permission(self, permission_mock):
        permission_mock.return_value = False
        response = self.client.post('/v2/indexdatadump/v1.1-1111-11-11-ror-data/prod')
        self.assertEqual(response.status_code, 403)

    @mock.patch.dict(os.environ, {"TOKEN": "token-value", "ROUTE_USER": "route-user"}, clear=False)
    @mock.patch('django.core.management.call_command')
    def test_index_ror_dump_fail_no_auth_headers(self, index_mock):
        index_mock.return_value = self.success_msg
        response = self.client.post('/v2/indexdatadump/v1.1-1111-11-11-ror-data/prod')
        self.assertEqual(response.status_code, 403)

    @mock.patch.dict(os.environ, {"TOKEN": "token-value", "ROUTE_USER": "route-user"}, clear=False)
    @mock.patch('django.core.management.call_command')
    def test_index_ror_dump_success_with_auth_headers(self, index_mock):
        index_mock.return_value = self.success_msg
        response = self.client.post(
            '/v2/indexdatadump/v1.1-1111-11-11-ror-data/prod',
            HTTP_TOKEN='token-value',
            HTTP_ROUTE_USER='route-user'
        )
        self.assertEqual(response.status_code, 200)