import json
import os
import re
import requests
import zipfile
import base64
from io import BytesIO
from rorapi.settings import ES7, ES_VARS, ROR_DUMP, DATA

from django.core.management.base import BaseCommand
from elasticsearch import TransportError

HEADERS = {'Accept': 'application/vnd.github.v3+json'}

def get_nested_names_v2(org):
    for name in org['names']:
        yield name['value']

def get_nested_ids_v2(org):
    yield org['id']
    yield re.sub('https://', '', org['id'])
    yield re.sub('https://ror.org/', '', org['id'])
    for ext_id in org['external_ids']:
        for eid in ext_id['all']:
            yield eid

def get_single_search_names_v2(org):
    for name in org["names"]:
        if "acronym" not in name["types"]:
            yield name["value"]

def get_affiliation_match_doc(org):
    doc = { 
        'id': org['id'],
        'country': org["locations"][0]["geonames_details"]["country_code"],
        'status': org['status'],
        'primary': [n["value"] for n in org["names"] if "ror_display" in n["types"]][0],
        'names': [{"name": n} for n in get_single_search_names_v2(org)],
        'relationships': [{"type": r['type'], "id": r['id']} for r in org['relationships']]
    }
    return doc

def index_dump(self, filename, index, dataset):
    backup_index = '{}-tmp'.format(index)
    ES7.reindex(body={
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
                        '_id': org['id']
                    }
                })
                org['names_ids'] = [{
                    'name': n
                } for n in get_nested_names_v2(org)]
                org['names_ids'] += [{
                    'id': n
                } for n in get_nested_ids_v2(org)]
                # experimental affiliations_match nested doc
                org['affiliation_match'] = get_affiliation_match_doc(org)
                body.append(org)
            ES7.bulk(body)
    except TransportError:
        self.stdout.write(TransportError)
        self.stdout.write('Reverting to backup index')
        ES7.reindex(body={
            'source': {
                'index': backup_index
            },
            'dest': {
                'index': index
            }
        })
    if ES7.indices.exists(backup_index):
        ES7.indices.delete(backup_index)
    self.stdout.write('ROR dataset ' + filename + ' indexed')


class Command(BaseCommand):
    help = 'Indexes ROR dataset from a full dump file in ror-data repo'

    def handle(self, *args, **options):
        json_files = []
        filename = options['filename']
        ror_dump_zip = filename + '.zip'
        if os.path.exists(ror_dump_zip):
            if not os.path.exists(DATA['WORKING_DIR']):
                os.makedirs(DATA['WORKING_DIR'])
            self.stdout.write('Extracting ROR dump')
            with zipfile.ZipFile(ror_dump_zip, 'r') as zip_ref:
                zip_ref.extractall(DATA['WORKING_DIR'] + filename)
            unzipped_files = os.listdir(DATA['WORKING_DIR'] + filename)
            for file in unzipped_files:
                if file.endswith(".json"):
                    json_files.append(file)
            if json_files:
                for json_file in json_files:
                    json_path = os.path.join(DATA['WORKING_DIR'], filename, '') + json_file
                    # Check if file is v2.0+ format or legacy schema_v2 format
                    version_match = re.match(r'v(\d+)\.(\d+)', json_file)
                    is_v2_format = False
                    if version_match:
                        major, minor = map(int, version_match.groups())
                        if major >= 2:
                            is_v2_format = True
                    elif 'schema_v2' in json_file:
                        # Legacy format with schema_v2 in filename
                        is_v2_format = True
                    
                    if is_v2_format and (options.get('schema') == 2 or options.get('schema') is None):
                        self.stdout.write('Loading JSON')
                        with open(json_path, 'r') as it:
                            dataset = json.load(it)
                        self.stdout.write('Indexing ROR dataset ' + json_file)
                        index = ES_VARS['INDEX_V2']
                        index_dump(self, json_file, index, dataset)
            else:
                self.stdout.write("ROR data dump does not contain any JSON files")

        else:
            self.stdout.write("ROR data dump zip file does not exist")
