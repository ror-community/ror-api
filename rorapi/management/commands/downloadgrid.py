import os
import requests
import zipfile

from django.core.management.base import BaseCommand
from rorapi.settings import GRID


class Command(BaseCommand):
    help = 'Downloads GRID dataset'

    def handle(self, *args, **options):
        os.makedirs(GRID['DIR'], exist_ok=True)

        # make sure we are not overwriting an existing ROR JSON file
        # with new ROR identifiers
        if zipfile.is_zipfile(GRID['ROR_ZIP_PATH']):
            self.stdout.write('Already downloaded GRID version {}'
                              .format(GRID['VERSION']))
            return

        self.stdout.write('Downloading GRID version {}'
                          .format(GRID['VERSION']))
        r = requests.get(GRID['URL'])
        with open(GRID['GRID_ZIP_PATH'], 'wb') as f:
            f.write(r.content)

        with zipfile.ZipFile(GRID['GRID_ZIP_PATH'], 'r') as zip_ref:
            zip_ref.extractall(GRID['DIR'])
