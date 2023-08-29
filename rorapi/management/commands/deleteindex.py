from rorapi.settings import ES7, ES_VARS

from django.core.management.base import BaseCommand

def delete_index(self, index):
    if ES7.indices.exists(index):
        ES7.indices.delete(index=index)
        self.stdout.write('Deleted index {}'.format(index))
    else:
        self.stdout.write('Index {} does not exist'.format(index))

class Command(BaseCommand):
    help = 'Deletes ROR API index'

    def handle(self, *args, **options):
        if(options['version']==1 or options['version'] is None):
            print("deleting v1 index")
            delete_index(self, ES_VARS['INDEX_V1'])
        if(options['version']==2 or options['version'] is None):
            print("deleting v2 index")
            delete_index(self, ES_VARS['INDEX_V2'])

