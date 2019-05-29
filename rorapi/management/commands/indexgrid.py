import json
import rorapi.settings

from django.core.management.base import BaseCommand
from elasticsearch import TransportError


class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def handle(self, *args, **options):
        with open(rorapi.settings.GRID['ROR_PATH'], 'r') as it:
            dataset = json.load(it)

        self.stdout.write('Indexing ROR dataset')

        index = rorapi.settings.ES_VARS['INDEX']
        backup_index = '{}-tmp'.format(index)
        rorapi.settings.ES.reindex(body={'source': {'index': index},
                         'dest': {'index': backup_index}})

        try:
            for i in range(0, len(dataset), rorapi.settings.ES_VARS['BATCH_SIZE']):
                body = []
                for org in dataset[i:i+rorapi.settings.ES_VARS['BATCH_SIZE']]:
                    body.append({'index': {'_index': index,
                                           '_type': 'org',
                                           '_id': org['id']}})
                    body.append(org)
                rorapi.settings.ES.bulk(body)
        except TransportError:
            rorapi.settings.ES.reindex(body={'source': {'index': backup_index},
                             'dest': {'index': index}})

        if rorapi.settings.ES.indices.exists(backup_index):
            rorapi.settings.ES.indices.delete(backup_index)
        self.stdout.write('ROR dataset indexed')
