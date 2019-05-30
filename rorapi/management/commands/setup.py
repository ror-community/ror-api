from django.core.management.base import BaseCommand
from .deleteindex import Command as DeleteIndexCommand
from .createindex import Command as CreateIndexCommand
from .indexgrid import Command as IndexGridCommand


class Command(BaseCommand):
    help = 'Setup ROR API'

    def handle(self, *args, **options):
        DeleteIndexCommand().handle(args, options)
        CreateIndexCommand().handle(args, options)
        IndexGridCommand().handle(args, options)
