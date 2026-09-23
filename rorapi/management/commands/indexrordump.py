import json
import os
import re
import requests
import zipfile
import base64
from io import BytesIO
from rorapi.settings import ES_VARS, ROR_DUMP, DATA
from rorapi.common.index_helpers import bulk_index_with_backup

from django.core.management.base import BaseCommand
from elasticsearch import TransportError

HEADERS = {'Accept': 'application/vnd.github.v3+json'}

def index_dump(self, filename, index, dataset):
    def on_transport_error(_exc):
        # Preserve prior logging: write the exception class name, then revert message.
        self.stdout.write(TransportError)
        self.stdout.write('Reverting to backup index')

    bulk_index_with_backup(index, dataset, on_transport_error=on_transport_error)
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
