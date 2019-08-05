import zipfile

from django.core.management.base import BaseCommand
from .deleteindex import Command as DeleteIndexCommand
from .createindex import Command as CreateIndexCommand
from .indexgrid import Command as IndexGridCommand
from rorapi.settings import GRID


class Command(BaseCommand):
    help = 'Setup ROR API'

    def handle(self, *args, **options):
        # make sure ROR JSON file exists
        if not zipfile.is_zipfile(GRID['ROR_ZIP_PATH']):
            self.stdout.write('ROR dataset for GRID version {} not found. '.
                              format(GRID['VERSION']) +
                              'Please run the upgrade command first.')
            return

        DeleteIndexCommand().handle(args, options)
        CreateIndexCommand().handle(args, options)
        IndexGridCommand().handle(args, options)
