from rorapi.settings import ES, ES7, ES_VARS

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Deletes ROR API index'

    def handle(self, *args, **options):
        es_version = options['esversion']
        index = ES_VARS['INDEX']
        if es_version == 7:
            print("deleting index on ES7")
            if ES.indices.exists(index):
                ES.indices.delete(index=index)
                self.stdout.write('Deleted index {}'.format(index))
            else:
                self.stdout.write('Index {} does not exist'.format(index))
        else:
            print("deleting index on ES6")
            if ES.indices.exists(index):
                ES.indices.delete(index=index)
                self.stdout.write('Deleted index {}'.format(index))
            else:
                self.stdout.write('Index {} does not exist'.format(index))
