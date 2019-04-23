import json

from django.core.management.base import BaseCommand
from elasticsearch import Elasticsearch
from rorapi.settings import ES


class Command(BaseCommand):
    help = 'Create ROR API index'

    def handle(self, *args, **options):
        es = Elasticsearch(ES['HOSTS'])

        if es.indices.exists(ES['INDEX']):
            self.stdout.write('Index {} already exists'.format(ES['INDEX']))
        else:
            with open(ES['INDEX_TEMPLATE'], 'r') as it:
                template = json.load(it)
            es.indices.create(index=ES['INDEX'], body=template)
            self.stdout.write('Created index {}'.format(ES['INDEX']))
