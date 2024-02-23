import requests
import zipfile

from django.core.management.base import BaseCommand
from rorapi.management.commands.deleteindex import Command as DeleteIndexCommand
from rorapi.management.commands.createindex import Command as CreateIndexCommand
from rorapi.management.commands.indexrordump import Command as IndexRorDumpCommand
from rorapi.settings import ROR_DUMP

HEADERS = {'Accept': 'application/vnd.github.v3+json'}

def get_ror_dump_sha(filename, use_test_data):
    sha = ''
    if use_test_data:
        contents_url = ROR_DUMP['TEST_REPO_URL'] + '/contents'
    else:
        contents_url = ROR_DUMP['PROD_REPO_URL'] + '/contents'
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
        parser.add_argument('-s', '--schema', type=int, choices=[1, 2], help='Schema version to index if only indexing 1 version. Only set if not indexing both versions.')
        parser.add_argument('-t', '--testdata', action='store_true', help='Set flag to pull data dump from ror-data-test instead of ror-data')

    def handle(self, *args, **options):
        msg = None
        # make sure ROR dump file exists
        filename = options['filename']
        use_test_data = options['testdata']
        if use_test_data:
            print("Using ror-data-test repo")
        else:
            print("Using ror-data repo")

        sha = get_ror_dump_sha(filename, use_test_data)

        if sha:
            DeleteIndexCommand().handle(*args, **options)
            CreateIndexCommand().handle(*args, **options)
            IndexRorDumpCommand().handle(*args, **options)
            msg = 'SUCCESS: ROR dataset {} indexed in version {}. Using test repo: {}'.format(filename, str(options['schema']), str(use_test_data))
        else:
            msg = 'ERROR: ROR dataset for file {} not found. '.format(filename) \
                +'Please generate the data dump first.'
            self.stdout.write(msg)

        return msg

