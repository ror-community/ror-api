import json
from rorapi.settings import ES, ES_VARS

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create ROR API index'

    def handle(self, *args, **options):
        index = ES_VARS['INDEX']
        if ES.indices.exists(index):
            self.stdout.write('Index {} already exists'.format(index))
        else:
            with open(ES_VARS['INDEX_TEMPLATE'], 'r') as it:
                template = json.load(it)
            ES.indices.put_template(index, template)
            self.stdout.write('Updated index template for {}'.format(index))
            ES.indices.create(index=index)
            self.stdout.write('Created index {}'.format(index))
