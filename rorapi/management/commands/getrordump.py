import json
import os
import re
import requests
import zipfile
import base64
from io import BytesIO
from rorapi.settings import ES7, ES_VARS, ROR_DUMP, DATA
from django.core.management.base import BaseCommand

HEADERS = {'Accept': 'application/vnd.github.v3+json'}
AUTH_HEADERS = {'Authorization': 'token {}'.format(ROR_DUMP['GITHUB_TOKEN']), 'Accept': 'application/vnd.github.v3+json'}

def get_ror_dump_sha(filename, use_test_data, github_headers):
    sha = ''
    if use_test_data:
        contents_url = ROR_DUMP['TEST_REPO_URL'] + '/contents'
    else:
        contents_url = ROR_DUMP['PROD_REPO_URL'] + '/contents'
    try:
        response = requests.get(contents_url, headers=github_headers)
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

def get_ror_dump_zip(filename, use_test_data, github_headers):
    sha = get_ror_dump_sha(filename, use_test_data, github_headers)
    if sha:
        if use_test_data:
            blob_url = ROR_DUMP['TEST_REPO_URL'] + '/git/blobs/' + sha
        else:
            blob_url = ROR_DUMP['PROD_REPO_URL'] + '/git/blobs/' + sha
        try:
            response = requests.get(blob_url, headers=github_headers)
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
    help = 'Downloads a specified ROR data dump from Github'

    def handle(self, *args, **options):
        filename = options['filename']
        use_test_data = options['testdata']
        self.stdout.write('Getting ROR dump')
        if ROR_DUMP['GITHUB_TOKEN']:
            github_headers = AUTH_HEADERS
        else:
            github_headers = HEADERS
        ror_dump_zip = get_ror_dump_zip(filename, use_test_data, github_headers)
