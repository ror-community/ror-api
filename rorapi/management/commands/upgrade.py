from django.core.management.base import BaseCommand
from .downloadgrid import Command as DownloadGridCommand
from .convertgrid import Command as ConvertGridCommand


class Command(BaseCommand):
    help = 'Generate up-to-date ror.zip from GRID data'

    def handle(self, *args, **options):
        DownloadGridCommand().handle(args, options)
        ConvertGridCommand().handle(args, options)
