from django.core.management.base import BaseCommand
from .downloadgrid import Command as DownloadGridCommand
from .convertgrid import Command as ConvertGridCommand


class Command(BaseCommand):
    help = 'Upgrade ROR API with latest GRID data'

    def handle(self, *args, **options):
        DownloadGridCommand().handle(args, options)
        ConvertGridCommand().handle(args, options)
