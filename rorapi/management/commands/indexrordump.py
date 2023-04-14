import json
import os
import re
import requests
import zipfile
import base64
from io import BytesIO
from rorapi.settings import ES, ES7, ES_VARS, ROR_DUMP, DATA

from django.core.management.base import BaseCommand
from elasticsearch import TransportError

HEADERS = {'Accept': 'application/vnd.github.v3+json'}

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

def get_ror_dump_sha(filename):
    sha = ''
    contents_url = ROR_DUMP['REPO_URL'] + '/contents'
    try:
        response = requests.get(contents_url, headers=HEADERS)
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"{contents_url}: is Not reachable \nErr: {e}")
    try:
        repo_contents = response.json()
        for file in repo_contents:
            if filename in file['name']:
                sha = file['sha']
        return sha
    except:
        return None

def get_ror_dump_zip(filename):
    sha = get_ror_dump_sha(filename)
    if sha:
        blob_url = ROR_DUMP['REPO_URL'] + '/git/blobs/' + sha
        try:
            response = requests.get(blob_url, headers=HEADERS)
        except requests.exceptions.RequestException as e:
            raise SystemExit(f"Github blob is Not reachable \nErr: {e}")
        try:
            response_json = response.json()
            file_decoded = base64.b64decode(response_json['content'])
            with open(filename + '.zip', 'wb') as zip_file:
                zip_file.write(file_decoded)
            return zip_file.name
        except:
            return None

class Command(BaseCommand):
    help = 'Indexes ROR dataset from a full dump file in ror-data repo'

    def handle(self, *args, **options):
        es_version = options['esversion']
        json_file = ''
        filename = options['filename']
        ror_dump_zip = get_ror_dump_zip(filename)
        if ror_dump_zip:
            if not os.path.exists(DATA['WORKING_DIR']):
                os.makedirs(DATA['WORKING_DIR'])
            with zipfile.ZipFile(ror_dump_zip, 'r') as zip_ref:
                zip_ref.extractall(DATA['WORKING_DIR'] + filename)
            unzipped_files = os.listdir(DATA['WORKING_DIR'] + filename)
            for file in unzipped_files:
                if file.endswith(".json"):
                    json_file = file
            json_path = os.path.join(DATA['WORKING_DIR'], filename, '') + json_file
            with open(json_path, 'r') as it:
                dataset = json.load(it)

            self.stdout.write('Indexing ROR dataset ' + filename)

            index = ES_VARS['INDEX']
            backup_index = '{}-tmp'.format(index)
            if es_version == 7:
                ES7.reindex(body={
                    'source': {
                        'index': index
                    },
                    'dest': {
                        'index': backup_index
                    }
                })
            else:
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
                        if es_version == 7:
                            body.append({
                                'index': {
                                    '_index': index,
                                    '_id': org['id']
                                }
                            })
                        else:
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
                    if es_version == 7:
                        ES7.bulk(body)
                    else:
                        ES.bulk(body)
            except TransportError:
                self.stdout.write(TransportError)
                self.stdout.write('Reverting to backup index')
                if es_version == 7:
                     ES7.reindex(body={
                        'source': {
                            'index': backup_index
                        },
                        'dest': {
                            'index': index
                        }
                    })
                else:
                    ES.reindex(body={
                        'source': {
                            'index': backup_index
                        },
                        'dest': {
                            'index': index
                        }
                    })
            if es_version == 7:
                if ES7.indices.exists(backup_index):
                    ES7.indices.delete(backup_index)
            else:
                if ES.indices.exists(backup_index):
                    ES.indices.delete(backup_index)
            self.stdout.write('ROR dataset ' + filename + ' indexed to ES version ' + str(es_version))
        else:
            print("ROR data dump zip file does not exist")
