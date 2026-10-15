from rorapi.settings import ES7, ES_VARS
from rorapi.v2.index_template import index_template

from django.core.management.base import BaseCommand


def create_index(self, index, template):
    ES7.indices.put_template(index, template)
    self.stdout.write('Updated index template for {}'.format(index))
    ES7.indices.create(index=index)
    self.stdout.write('Created index {}'.format(index))

class Command(BaseCommand):
    help = 'Create ROR API v2 index'

    def handle(self, *args, **options):
        self.stdout.write("creating v2 index")
        create_index(self, ES_VARS['INDEX_V2'], index_template())