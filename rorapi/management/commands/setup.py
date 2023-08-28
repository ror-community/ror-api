import requests
import zipfile

from django.core.management.base import BaseCommand
from rorapi.management.deleteindex import Command as DeleteIndexCommand
from rorapi.management.createindex import Command as CreateIndexCommand
from rorapi.management.indexrordump import Command as IndexRorDumpCommand
from rorapi.settings import ROR_DUMP

HEADERS = {'Accept': 'application/vnd.github.v3+json'}

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

class Command(BaseCommand):
    help = 'Setup ROR API'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, help='Name of data dump zip file to index without extension')

    def handle(self, *args, **options):
        # make sure ROR dump file exists
        filename = options['filename']
        sha = get_ror_dump_sha(filename)

        if sha:
            DeleteIndexCommand().handle(*args, **options)
            CreateIndexCommand().handle(*args, **options)
            IndexRorDumpCommand().handle(*args, **options)

        else:
            self.stdout.write('ROR dataset for version {} not found. '.
                              format(filename) +
                              'Please generate the data dump first.')
            return

