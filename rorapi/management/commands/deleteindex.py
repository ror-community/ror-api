import rorapi.settings

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Deletes ROR API index'

    def handle(self, *args, **options):
        index = rorapi.settings.ES_VARS['INDEX']

        if rorapi.settings.ES.indices.exists(index):
            rorapi.settings.ES.indices.delete(index=index)
            self.stdout.write('Deleted index {}'.format(index))
        else:
            self.stdout.write('Index {} does not exist'.format(index))
