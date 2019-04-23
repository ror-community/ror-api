import json

from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch, TransportError
from rorapi.settings import ES, GRID


class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def handle(self, *args, **options):
        with open(GRID['ROR_PATH'], 'r') as it:
            dataset = json.load(it)

        es = Elasticsearch(ES['HOSTS'])

        self.stdout.write('Indexing ROR dataset')

        backup_index = '{}-tmp'.format(ES['INDEX'])
        es.reindex(body={'source': {'index': ES['INDEX']},
                         'dest': {'index': backup_index}})

        try:
            for i in range(0, len(dataset), ES['BATCH_SIZE']):
                body = []
                for org in dataset[i:i+ES['BATCH_SIZE']]:
                    body.append({'index': {'_index': ES['INDEX'],
                                           '_type': 'org',
                                           '_id': org['id']}})
                    body.append(org)
                es.bulk(body)
        except TransportError:
            es.reindex(body={'source': {'index': backup_index},
                             'dest': {'index': ES['INDEX']}})

        if es.indices.exists(backup_index):
            es.indices.delete(backup_index)
        self.stdout.write('ROR dataset indexed')
