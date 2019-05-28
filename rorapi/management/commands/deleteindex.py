import rorapi.settings

from django.core.management.base import BaseCommand
from elasticsearch_dsl import connections


class Command(BaseCommand):
    help = 'Deletes ROR API index'

    def handle(self, *args, **options):
        es = connections.get_connection()
        index = rorapi.settings.ES['INDEX']

        if es.indices.exists(index):
            es.indices.delete(index=index)
            self.stdout.write('Deleted index {}'.format(index))
        else:
            self.stdout.write('Index {} does not exist'.format(index))
