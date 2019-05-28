import os
import requests
import zipfile

from django.core.management.base import BaseCommand
from rorapi.settings import GRID


class Command(BaseCommand):
    help = 'Downloads GRID dataset'

    def handle(self, *args, **options):
        os.makedirs(GRID['DIR'], exist_ok=True)

        self.stdout.write('Downloading GRID version {}'
                          .format(GRID['VERSION']))
        r = requests.get(GRID['URL'])
        with open(GRID['ZIP_PATH'], 'wb') as f:
            f.write(r.content)

        with zipfile.ZipFile(GRID['ZIP_PATH'], 'r') as zip_ref:
            zip_ref.extractall(GRID['DIR'])
