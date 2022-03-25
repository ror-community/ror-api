from django.core.management.base import BaseCommand
from .downloadgrid import Command as DownloadGridCommand
from .convertgrid import Command as ConvertGridCommand

# Previously used to generate ROR dataset
# based on the latest GRID dataset configured in settings.py
# As of Mar 2022 ROR is no longer based on GRID
# New records are now created in https://github.com/ror-community/ror-records and pushed to S3
# Individual record files in S3 are indexed with indexror.py
# Entire dataset zip files in https://github.com/ror-community/ror-data
# can be indexed with setup.py, which uses indexrordump.py

class Command(BaseCommand):
    help = 'Generate up-to-date ror.zip from GRID data'

    def handle(self, *args, **options):
        DownloadGridCommand().handle(args, options)
        ConvertGridCommand().handle(args, options)
