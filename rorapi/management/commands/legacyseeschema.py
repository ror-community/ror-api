import json
from rorapi.settings import ES, ES_VARS

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create ROR API index'

    def handle(self, *args, **options):
        index = ES_VARS['INDEX']
        if ES.indices.exists(index):
            raw_data = ES.indices.get_mapping( index )
            schema = raw_data[ index ]["mappings"]["org"]
            print (json.dumps(schema, indent=4))
        else:
            with open(ES_VARS['INDEX_TEMPLATE'], 'r') as it:
                template = json.load(it)
            ES.indices.create(index=index, body=template)
            self.stdout.write('Created index {}'.format(index))
