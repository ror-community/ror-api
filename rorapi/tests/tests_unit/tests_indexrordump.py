import mock
from io import StringIO

from django.core.management.base import OutputWrapper
from django.test import SimpleTestCase
from elasticsearch import TransportError

from rorapi.common.es_bulk import bulk_with_retry, is_retryable
from rorapi.management.commands import indexrordump
from rorapi.settings import ES_VARS


class BulkWithRetryTestCase(SimpleTestCase):

    def test_is_retryable_429(self):
        self.assertTrue(is_retryable(TransportError(429, 'Too Many Requests')))

    def test_is_retryable_503(self):
        self.assertTrue(is_retryable(TransportError(503, 'Service Unavailable')))

    def test_is_retryable_400_not_retryable(self):
        self.assertFalse(is_retryable(TransportError(400, 'Bad Request')))

    @mock.patch('rorapi.common.es_bulk.time.sleep')
    def test_retries_then_succeeds(self, sleep_mock):
        es_client = mock.Mock()
        es_client.bulk.side_effect = [
            TransportError(429, 'Too Many Requests'),
            {'_items': []},
        ]
        result = bulk_with_retry(es_client, [{'index': {}}], max_attempts=3, base_delay=0.01)
        self.assertEqual(result, {'_items': []})
        self.assertEqual(es_client.bulk.call_count, 2)
        sleep_mock.assert_called_once()

    @mock.patch('rorapi.common.es_bulk.time.sleep')
    def test_exhausted_retries_reraises(self, sleep_mock):
        es_client = mock.Mock()
        es_client.bulk.side_effect = TransportError(429, 'Too Many Requests')
        with self.assertRaises(TransportError) as ctx:
            bulk_with_retry(es_client, [{'index': {}}], max_attempts=3, base_delay=0.01)
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(es_client.bulk.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)

    def test_non_retryable_raises_immediately(self):
        es_client = mock.Mock()
        es_client.bulk.side_effect = TransportError(400, 'Bad Request')
        with self.assertRaises(TransportError):
            bulk_with_retry(es_client, [{'index': {}}], max_attempts=5, base_delay=0.01)
        self.assertEqual(es_client.bulk.call_count, 1)


class IndexDumpTestCase(SimpleTestCase):

    def setUp(self):
        self.command = mock.Mock()
        self.command.stdout = OutputWrapper(StringIO())
        self.dataset = [
            {
                'id': 'https://ror.org/01an7q238',
                'status': 'active',
                'names': [
                    {'value': 'University of Example', 'types': ['ror_display', 'label']},
                ],
                'external_ids': [],
                'locations': [
                    {'geonames_details': {'country_code': 'US'}},
                ],
                'relationships': [],
            }
        ]
        self.index = ES_VARS['INDEX_V2']
        self.backup_index = '{}-tmp'.format(self.index)

    @mock.patch('rorapi.management.commands.indexrordump.bulk_with_retry')
    @mock.patch('rorapi.management.commands.indexrordump.ES7')
    def test_retry_success_skips_rollback(self, es7_mock, bulk_mock):
        # setup already created -tmp; do not overwrite it
        es7_mock.indices.exists.side_effect = lambda name: name == self.backup_index
        bulk_mock.return_value = {'_items': []}

        indexrordump.index_dump(self.command, 'test.json', self.index, self.dataset)

        bulk_mock.assert_called_once()
        # delete backup after success; no restore reindex
        es7_mock.indices.delete.assert_called_once_with(self.backup_index)
        reindex_calls = es7_mock.reindex.call_args_list
        self.assertEqual(reindex_calls, [])
        output = self.command.stdout.getvalue()
        self.assertIn('indexed', output)
        self.assertNotIn('Reverting', output)

    @mock.patch('rorapi.management.commands.indexrordump.bulk_with_retry')
    @mock.patch('rorapi.management.commands.indexrordump.ES7')
    def test_exhausted_429_rolls_back_and_reraises(self, es7_mock, bulk_mock):
        es7_mock.indices.exists.return_value = True
        bulk_mock.side_effect = TransportError(429, 'Too Many Requests')

        with self.assertRaises(TransportError) as ctx:
            indexrordump.index_dump(self.command, 'test.json', self.index, self.dataset)

        self.assertEqual(ctx.exception.status_code, 429)
        output = self.command.stdout.getvalue()
        self.assertIn('Too Many Requests', output)
        self.assertIn('Reverting to backup index', output)
        self.assertNotIn('indexed', output)

        found_restore = False
        for call in es7_mock.reindex.call_args_list:
            body = call.kwargs.get('body')
            if body is None and call.args:
                body = call.args[0]
            if body and body.get('source', {}).get('index') == self.backup_index:
                found_restore = True
                break
        self.assertTrue(found_restore, 'expected restore reindex from backup')
        es7_mock.indices.delete.assert_called_with(self.backup_index)

    @mock.patch('rorapi.management.commands.indexrordump.bulk_with_retry')
    @mock.patch('rorapi.management.commands.indexrordump.ES7')
    def test_logging_transport_error_instance_does_not_raise_attribute_error(
            self, es7_mock, bulk_mock):
        """Regression: writing TransportError class caused AttributeError on endswith."""
        es7_mock.indices.exists.return_value = True
        bulk_mock.side_effect = TransportError(429, 'Too Many Requests')

        with self.assertRaises(TransportError):
            indexrordump.index_dump(self.command, 'test.json', self.index, self.dataset)

        # If the old bug returned (stdout.write(TransportError class)), Django would
        # raise AttributeError before we could re-raise TransportError.
        output = self.command.stdout.getvalue()
        self.assertIn('TransportError', output)
        self.assertIn('429', output)


class SetupBackupTestCase(SimpleTestCase):

    @mock.patch('rorapi.management.commands.setup.ES7')
    def test_backup_live_index_reindexes_when_live_exists(self, es7_mock):
        from rorapi.management.commands.setup import backup_live_index

        index = ES_VARS['INDEX_V2']
        backup = '{}-tmp'.format(index)
        es7_mock.indices.exists.side_effect = lambda name: name == index
        stdout = OutputWrapper(StringIO())

        backup_live_index(stdout)

        es7_mock.reindex.assert_called_once()
        body = es7_mock.reindex.call_args.kwargs.get('body') or es7_mock.reindex.call_args.args[0]
        self.assertEqual(body['source']['index'], index)
        self.assertEqual(body['dest']['index'], backup)
        self.assertIn('Backed up', stdout.getvalue())

    @mock.patch('rorapi.management.commands.setup.ES7')
    def test_backup_live_index_skips_when_missing(self, es7_mock):
        from rorapi.management.commands.setup import backup_live_index

        es7_mock.indices.exists.return_value = False
        stdout = OutputWrapper(StringIO())

        backup_live_index(stdout)

        es7_mock.reindex.assert_not_called()
        self.assertIn('No existing', stdout.getvalue())
