import json
import re
import zipfile
from rorapi.settings import ES, ES_VARS, GRID, ROR_DUMP

from django.core.management.base import BaseCommand
from elasticsearch import TransportError


def get_nested_names(org):
    yield org['name']
    for label in org['labels']:
        yield label['label']
    for alias in org['aliases']:
        yield alias
    for acronym in org['acronyms']:
        yield acronym


def get_nested_ids(org):
    yield org['id']
    yield re.sub('https://', '', org['id'])
    yield re.sub('https://ror.org/', '', org['id'])
    for ext_name, ext_id in org['external_ids'].items():
        if ext_name == 'GRID':
            yield ext_id['all']
        else:
            for eid in ext_id['all']:
                yield eid


class Command(BaseCommand):
    help = 'Indexes ROR dataset'

    def handle(self, *args, **options):
        with zipfile.ZipFile(ROR_DUMP['ROR_ZIP_PATH'], 'r') as zip_ref:
            zip_ref.extractall(ROR_DUMP['DIR'])

        with open(ROR_DUMP['ROR_JSON_PATH'], 'r') as it:
            dataset = json.load(it)

        self.stdout.write('Indexing ROR dataset')

        index = ES_VARS['INDEX']
        backup_index = '{}-tmp'.format(index)
        ES.reindex(body={
            'source': {
                'index': index
            },
            'dest': {
                'index': backup_index
            }
        })

        try:
            for i in range(0, len(dataset), ES_VARS['BULK_SIZE']):
                body = []
                for org in dataset[i:i + ES_VARS['BULK_SIZE']]:
                    body.append({
                        'index': {
                            '_index': index,
                            '_type': 'org',
                            '_id': org['id']
                        }
                    })
                    org['names_ids'] = [{
                        'name': n
                    } for n in get_nested_names(org)]
                    org['names_ids'] += [{
                        'id': n
                    } for n in get_nested_ids(org)]
                    body.append(org)
                ES.bulk(body)
        except TransportError:
            self.stdout.write(TransportError)
            ES.reindex(body={
                'source': {
                    'index': backup_index
                },
                'dest': {
                    'index': index
                }
            })

        if ES.indices.exists(backup_index):
            ES.indices.delete(backup_index)
        self.stdout.write('ROR dataset indexed')
