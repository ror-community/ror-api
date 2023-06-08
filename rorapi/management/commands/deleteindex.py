from rorapi.settings import ES7, ES_VARS

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Deletes ROR API index'

    def handle(self, *args, **options):
        index = ES_VARS['INDEX']
        print("deleting index")
        if ES7.indices.exists(index):
            ES7.indices.delete(index=index)
            self.stdout.write('Deleted index {}'.format(index))
        else:
            self.stdout.write('Index {} does not exist'.format(index))
