import requests
import zipfile

from django.core.management.base import BaseCommand
from .deleteindex import Command as DeleteIndexCommand
from .createindex import Command as CreateIndexCommand
from .indexrordump import Command as IndexRorDumpCommand
from rorapi.settings import GRID, ROR_DUMP


class Command(BaseCommand):
    help = 'Setup ROR API'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, help='Name of data dump zip file to index without extension')

    def handle(self, *args, **options):
        # make sure ROR dump file exists
        filename = options['filename']
        url = ROR_DUMP['URL'] + filename + '.zip'
        print(url)
        ror_dump_zip = requests.get(url)

        if ror_dump_zip.status_code == 200:
            DeleteIndexCommand().handle(*args, **options)
            CreateIndexCommand().handle(*args, **options)
            IndexRorDumpCommand().handle(*args, **options)

        else:
            self.stdout.write('ROR dataset for version {} not found. '.
                              format(filename) +
                              'Please generate the data dump first.')
            return

