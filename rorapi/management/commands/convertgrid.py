import base32_crockford
import json
import os.path
import random
import zipfile
from rorapi.settings import ES, ES_VARS, ROR_API, GRID

from django.core.management.base import BaseCommand


def generate_ror_id():
    """Generates random ROR ID.

    The checksum calculation is copied from
    https://github.com/datacite/base32-url/blob/master/lib/base32/url.rb
    to maintain the compatibility with previously generated ROR IDs.
    """

    n = random.randint(0, 200000000)
    n_encoded = base32_crockford.encode(n).lower().zfill(6)
    checksum = str(98 - ((n * 100) % 97)).zfill(2)
    return '{}0{}{}'.format(ROR_API['ID_PREFIX'], n_encoded, checksum)


def get_ror_id(grid_id, es):
    """Maps GRID ID to ROR ID.

    If given GRID ID was indexed previously, corresponding ROR ID is obtained
    from the index. Otherwise, new ROR ID is generated.
    """

    s = ES.search(ES_VARS['INDEX'],
                  body={'query': {
                      'term': {
                          'external_ids.GRID.all': grid_id
                      }
                  }})
    if s['hits']['total'] == 1:
        return s['hits']['hits'][0]['_id']
    return generate_ror_id()


def convert_organization(grid_org, es):
    """Converts the organization metadata from GRID schema to ROR schema."""

    return {
        'id':
        get_ror_id(grid_org['id'], ES),
        'name':
        grid_org['name'],
        'types':
        grid_org['types'],
        'links':
        grid_org['links'],
        'aliases':
        grid_org['aliases'],
        'acronyms':
        grid_org['acronyms'],
        'status':
        grid_org['status'],
        'wikipedia_url':
        grid_org['wikipedia_url'],
        'labels':
        grid_org['labels'],
        'country': {
            'country_code': grid_org['addresses'][0]['country_code'],
            'country_name': grid_org['addresses'][0]['country']
        },
        'external_ids':
        dict(grid_org.get('external_ids', {}),
             GRID={
                 'preferred': grid_org['id'],
                 'all': grid_org['id']
             })
    }


class Command(BaseCommand):
    help = 'Converts GRID dataset to ROR schema'

    def handle(self, *args, **options):
        # make sure we are not overwriting an existing ROR JSON file
        # with new ROR identifiers
        if zipfile.is_zipfile(GRID['ROR_ZIP_PATH']):
            self.stdout.write('GRID dataset already converted')
            return

        if not os.path.isfile(GRID['ROR_JSON_PATH']):
            with open(GRID['GRID_JSON_PATH'], 'r') as it:
                grid_data = json.load(it)

            self.stdout.write('Converting GRID dataset to ROR schema')
            ror_data = [
                convert_organization(org, ES)
                for org in grid_data['institutes'] if org['status'] == 'active'
            ]
            with open(GRID['ROR_JSON_PATH'], 'w') as outfile:
                json.dump(ror_data, outfile, indent=4)
            self.stdout.write('GRID dataset converted')

        # generate zip archive
        with zipfile.ZipFile(GRID['ROR_ZIP_PATH'], 'w') as zipArchive:
            zipArchive.write(GRID['ROR_JSON_PATH'],
                             arcname='ror.json',
                             compress_type=zipfile.ZIP_DEFLATED)
            self.stdout.write('ROR dataset ZIP archive created')
