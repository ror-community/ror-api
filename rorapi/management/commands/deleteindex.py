from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch
from rorapi.settings import ES


class Command(BaseCommand):
    help = 'Deletes ROR API index'

    def handle(self, *args, **options):
        es = Elasticsearch(ES['HOSTS'])

        if es.indices.exists(ES['INDEX']):
            es.indices.delete(index=ES['INDEX'])
            self.stdout.write('Deleted index {}'.format(ES['INDEX']))
        else:
            self.stdout.write('Index {} does not exist'.format(ES['INDEX']))
