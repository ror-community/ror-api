import json
import rorapi.settings

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create ROR API index'

    def handle(self, *args, **options):
        index = rorapi.settings.ES_VARS['INDEX']
        if rorapi.settings.ES.indices.exists(index):
            self.stdout.write('Index {} already exists'.format(index))
        else:
            with open(rorapi.settings.ES_VARS['INDEX_TEMPLATE'], 'r') as it:
                template = json.load(it)
            rorapi.settings.ES.indices.create(index=index, body=template)
            self.stdout.write('Created index {}'.format(index))
