from unittest import mock

from django.test import SimpleTestCase
from elasticsearch import TransportError

from rorapi.common import index_helpers
from rorapi.settings import ES_VARS


SAMPLE_ORG = {
    'id': 'https://ror.org/01an7q238',
    'status': 'active',
    'names': [
        {'value': 'University of Example', 'types': ['ror_display', 'label']},
        {'value': 'UoE', 'types': ['acronym']},
        {'value': 'Example U', 'types': ['alias']},
    ],
    'external_ids': [
        {'type': 'grid', 'all': ['grid.1234.5']},
    ],
    'locations': [
        {'geonames_details': {'country_code': 'US'}},
    ],
    'relationships': [
        {'type': 'parent', 'id': 'https://ror.org/05dxps055'},
    ],
}


class IndexDocBuildersTestCase(SimpleTestCase):

    def test_get_nested_names_v2(self):
        self.assertEqual(
            list(index_helpers.get_nested_names_v2(SAMPLE_ORG)),
            ['University of Example', 'UoE', 'Example U'],
        )

    def test_get_nested_ids_v2(self):
        self.assertEqual(
            list(index_helpers.get_nested_ids_v2(SAMPLE_ORG)),
            [
                'https://ror.org/01an7q238',
                'ror.org/01an7q238',
                '01an7q238',
                'grid.1234.5',
            ],
        )

    def test_get_single_search_names_v2_skips_acronyms(self):
        self.assertEqual(
            list(index_helpers.get_single_search_names_v2(SAMPLE_ORG)),
            ['University of Example', 'Example U'],
        )

    def test_get_affiliation_match_doc(self):
        doc = index_helpers.get_affiliation_match_doc(SAMPLE_ORG)
        self.assertEqual(doc['id'], SAMPLE_ORG['id'])
        self.assertEqual(doc['country'], 'US')
        self.assertEqual(doc['status'], 'active')
        self.assertEqual(doc['primary'], 'University of Example')
        self.assertEqual(
            doc['names'],
            [{'name': 'University of Example'}, {'name': 'Example U'}],
        )
        self.assertEqual(
            doc['relationships'],
            [{'type': 'parent', 'id': 'https://ror.org/05dxps055'}],
        )

    def test_enrich_org_for_index(self):
        org = dict(SAMPLE_ORG)
        index_helpers.enrich_org_for_index(org)
        self.assertIn({'name': 'University of Example'}, org['names_ids'])
        self.assertIn({'id': '01an7q238'}, org['names_ids'])
        self.assertEqual(org['affiliation_match']['primary'], 'University of Example')
        self.assertEqual(org['acronyms'], ['UoE'])


class BulkIndexWithBackupTestCase(SimpleTestCase):

    def setUp(self):
        self.index = ES_VARS['INDEX_V2']
        self.backup_index = '{}-tmp'.format(self.index)
        self.dataset = [dict(SAMPLE_ORG)]

    def _mock_live_index(self, es7_mock, backup_already=False):
        state = {'backup': backup_already}

        def exists(name):
            if name == self.backup_index:
                return state['backup']
            return name == self.index

        def reindex(*args, **kwargs):
            body = kwargs.get('body')
            if body is None and args:
                body = args[0]
            if body and body.get('dest', {}).get('index') == self.backup_index:
                state['backup'] = True

        es7_mock.indices.exists.side_effect = exists
        es7_mock.reindex.side_effect = reindex
        es7_mock.count.return_value = {'count': 2}

    @mock.patch('rorapi.common.index_helpers.ES7')
    def test_success_backs_up_bulks_and_deletes_backup(self, es7_mock):
        self._mock_live_index(es7_mock)
        bulk_mock = mock.Mock(return_value={'_items': []})

        ok = index_helpers.bulk_index_with_backup(
            self.index, self.dataset, bulk=bulk_mock)

        self.assertTrue(ok)
        bulk_mock.assert_called_once()
        body = bulk_mock.call_args.args[0]
        self.assertEqual(body[0]['index']['_index'], self.index)
        self.assertEqual(body[0]['index']['_id'], SAMPLE_ORG['id'])
        self.assertEqual(body[1]['affiliation_match']['primary'], 'University of Example')
        es7_mock.indices.delete.assert_called_once_with(self.backup_index)
        # backup reindex only (no restore)
        self.assertEqual(es7_mock.reindex.call_count, 1)

    @mock.patch('rorapi.common.index_helpers.ES7')
    def test_existing_backup_is_not_overwritten(self, es7_mock):
        self._mock_live_index(es7_mock, backup_already=True)
        bulk_mock = mock.Mock(return_value={'_items': []})

        ok = index_helpers.bulk_index_with_backup(
            self.index, self.dataset, bulk=bulk_mock)

        self.assertTrue(ok)
        es7_mock.reindex.assert_not_called()
        es7_mock.indices.delete.assert_called_once_with(self.backup_index)

    @mock.patch('rorapi.common.index_helpers.ES7')
    def test_transport_error_rolls_back_and_calls_hook(self, es7_mock):
        self._mock_live_index(es7_mock)
        bulk_mock = mock.Mock(side_effect=TransportError(429, 'Too Many Requests'))
        on_error = mock.Mock()

        ok = index_helpers.bulk_index_with_backup(
            self.index, self.dataset, on_transport_error=on_error, bulk=bulk_mock)

        self.assertFalse(ok)
        on_error.assert_called_once()
        self.assertEqual(es7_mock.reindex.call_count, 2)
        restore_body = es7_mock.reindex.call_args_list[1].kwargs.get('body')
        if restore_body is None:
            restore_body = es7_mock.reindex.call_args_list[1].args[0]
        self.assertEqual(restore_body['source']['index'], self.backup_index)
        self.assertEqual(restore_body['dest']['index'], self.index)
        es7_mock.indices.delete.assert_called_once_with(self.backup_index)

    @mock.patch('rorapi.common.index_helpers.ES7')
    def test_empty_index_failure_clears_partial_documents(self, es7_mock):
        def exists(name):
            return name == self.index

        es7_mock.indices.exists.side_effect = exists
        es7_mock.count.return_value = {'count': 0}
        bulk_mock = mock.Mock(side_effect=TransportError(429, 'Too Many Requests'))
        on_error = mock.Mock()

        ok = index_helpers.bulk_index_with_backup(
            self.index, self.dataset, on_transport_error=on_error, bulk=bulk_mock)

        self.assertFalse(ok)
        on_error.assert_called_once()
        es7_mock.reindex.assert_not_called()
        es7_mock.indices.delete.assert_not_called()
        es7_mock.delete_by_query.assert_called_once_with(
            index=self.index,
            body={'query': {'match_all': {}}},
            params={'conflicts': 'proceed', 'refresh': True},
        )

    @mock.patch('rorapi.common.index_helpers.ES7')
    def test_missing_index_failure_deletes_index_created_by_bulk(self, es7_mock):
        live_checks = {'n': 0}

        def exists(name):
            if name == self.backup_index:
                return False
            live_checks['n'] += 1
            return live_checks['n'] > 1

        es7_mock.indices.exists.side_effect = exists
        bulk_mock = mock.Mock(side_effect=TransportError(503, 'Service Unavailable'))
        on_error = mock.Mock()

        ok = index_helpers.bulk_index_with_backup(
            self.index, self.dataset, on_transport_error=on_error, bulk=bulk_mock)

        self.assertFalse(ok)
        on_error.assert_called_once()
        es7_mock.reindex.assert_not_called()
        es7_mock.delete_by_query.assert_not_called()
        es7_mock.indices.delete.assert_called_once_with(self.index)
