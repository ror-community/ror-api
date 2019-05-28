from django.core.management.base import BaseCommand
from .createindex import Command as CreateIndexCommand
from .downloadgrid import Command as DownloadGridCommand
from .convertgrid import Command as ConvertGridCommand
from .indexgrid import Command as IndexGridCommand


class Command(BaseCommand):
    help = 'Setup ROR API'

    def handle(self, *args, **options):
        CreateIndexCommand().handle(args, options)
        DownloadGridCommand().handle(args, options)
        ConvertGridCommand().handle(args, options)
        IndexGridCommand().handle(args, options)
