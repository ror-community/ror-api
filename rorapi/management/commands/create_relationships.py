from .generaterelationships import generate_relationships

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Generate Relationships by passing a csv file with relationship detail'

    def add_arguments(self, parser):
        parser.add_argument('f', type=str, help='help for f')

    def handle(self, *args, **options):
        self.stdout.write("Creating relationships from relationships.csv")
        file = options['f']
        generate_relationships(file)
        self.stdout.write("Created relationships")
