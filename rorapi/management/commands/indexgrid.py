import json
import rorapi.settings

from django.core.management.base import BaseCommand
from elasticsearch import TransportError
from elasticsearch_dsl import connections


class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def handle(self, *args, **options):
        with open(rorapi.settings.GRID['ROR_PATH'], 'r') as it:
            dataset = json.load(it)

        es = connections.get_connection()

        self.stdout.write('Indexing ROR dataset')

        index = rorapi.settings.ES['INDEX']
        backup_index = '{}-tmp'.format(index)
        es.reindex(body={'source': {'index': index},
                         'dest': {'index': backup_index}})

        try:
            for i in range(0, len(dataset), rorapi.settings.ES['BATCH_SIZE']):
                body = []
                for org in dataset[i:i+rorapi.settings.ES['BATCH_SIZE']]:
                    body.append({'index': {'_index': index,
                                           '_type': 'org',
                                           '_id': org['id']}})
                    body.append(org)
                es.bulk(body)
        except TransportError:
            es.reindex(body={'source': {'index': backup_index},
                             'dest': {'index': index}})

        if es.indices.exists(backup_index):
            es.indices.delete(backup_index)
        self.stdout.write('ROR dataset indexed')
