import json
from rorapi.settings import ES7, ES_VARS

from django.core.management.base import BaseCommand


def create_index(self, index, template_file):
    with open(template_file, 'r') as it:
        template = json.load(it)
    ES7.indices.put_template(index, template)
    self.stdout.write('Updated index template for {}'.format(index))
    ES7.indices.create(index=index)
    self.stdout.write('Created index {}'.format(index))

class Command(BaseCommand):
    help = 'Create ROR API index'

    def handle(self, *args, **options):
        if(options['version']==1 or options['version'] is None):
            print("creating v1 index")
            create_index(self, ES_VARS['INDEX_V1'], ES_VARS['INDEX_TEMPLATE_ES7_V1'])
        if(options['version']==2 or options['version'] is None):
            print("creating v2 index")
            create_index(self, ES_VARS['INDEX_V2'], ES_VARS['INDEX_TEMPLATE_ES7_V2'])