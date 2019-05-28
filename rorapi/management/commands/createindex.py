import json
import rorapi.settings

from django.core.management.base import BaseCommand
from elasticsearch_dsl import connections


class Command(BaseCommand):
    help = 'Create ROR API index'

    def handle(self, *args, **options):
        es = connections.get_connection()

        index = rorapi.settings.ES['INDEX']
        if es.indices.exists(index):
            self.stdout.write('Index {} already exists'.format(index))
        else:
            with open(rorapi.settings.ES['INDEX_TEMPLATE'], 'r') as it:
                template = json.load(it)
            es.indices.create(index=index, body=template)
            self.stdout.write('Created index {}'.format(index))
