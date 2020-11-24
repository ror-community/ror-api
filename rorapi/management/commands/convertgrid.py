import base32_crockford
import json
import os.path
import random
import zipfile
import re
from rorapi.settings import ES, ES_VARS, ROR_API, GRID, ROR_DUMP

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

def geonames_city(geonames_city):
    geonames = ["geonames_admin1","geonames_admin2"]
    geonames_attributes = ["id","name","ascii_name","code"]
    nuts = ["nuts_level1","nuts_level2","nuts_level3"]
    nuts_attributes = ["code","name"]
    geonames_city_hsh = {}
    for k,v in geonames_city.items():
        if (k in geonames):
            if isinstance(v,dict):
                geonames_city_hsh[k] = {i:v.get(i,None) for i in geonames_attributes}
            elif v is None:
                geonames_city_hsh[k] = {i:None for i in geonames_attributes}
        elif (k in nuts):
            if isinstance(v,dict):
                geonames_city_hsh[k] = {i:v.get(i,None) for i in nuts_attributes}
            elif v is None:
                geonames_city_hsh[k] = {i:None for i in nuts_attributes}
        else:
            geonames_city_hsh[k] = v
    return geonames_city_hsh

def addresses(location):
    line = ""
    address = ["line_1", "line_2", "line_3"]
    combine_lines = address + ["country", "country_code"]
    geonames_admin = ["id","code","name","ascii_name"]
    nuts = ["code","name"]
    new_addresses = []
    hsh = {}
    hsh["line"] = None
    for h in location:
        for k, v in h.items():
            if not (k in combine_lines) and (k != "geonames_city"):
                hsh[k] = v
            elif k == "geonames_city":
                if isinstance(v,dict):
                    hsh[k] = geonames_city(v)
                elif v is None:
                    hsh[k] = {}
            elif (k in combine_lines):
                n = []
                for i in address:
                    if not (h[i] is None):
                        n.append(h[i])
                line = " ".join(n)
                line = re.sub(' +', ' ', line)
                if (len(line) == 1 and line == " "):
                    line = line.strip()
                hsh["line"] = line
        new_addresses.append(hsh)
    return new_addresses


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
        'email_address':
        grid_org['email_address'],
        'ip_addresses':
        grid_org['ip_addresses'],
        'established':
        grid_org['established'],
        'country': {
            'country_code': grid_org['addresses'][0]['country_code'],
            'country_name': grid_org['addresses'][0]['country']
        },
        'relationships':
        grid_org["relationships"],
        'addresses':
        addresses(grid_org["addresses"]),
        'external_ids':
        getExternalIds(
            dict(grid_org.get('external_ids', {}),
                 GRID={
                     'preferred': grid_org['id'],
                     'all': grid_org['id']
                 }))
    }


def getExternalIds(external_ids):
    if 'ROR' in external_ids: del external_ids['ROR']
    return external_ids


class Command(BaseCommand):
    help = 'Converts GRID dataset to ROR schema'

    def handle(self, *args, **options):
        os.makedirs(ROR_DUMP['DIR'], exist_ok=True)
        # make sure we are not overwriting an existing ROR JSON file
        # with new ROR identifiers
        if zipfile.is_zipfile(ROR_DUMP['ROR_ZIP_PATH']):
            self.stdout.write('ROR dataset already exists')
            return

        if not os.path.isfile(ROR_DUMP['ROR_JSON_PATH']):
            with open(GRID['GRID_JSON_PATH'], 'r') as it:
                grid_data = json.load(it)

            self.stdout.write('Converting GRID dataset to ROR schema')
            ror_data = [
                convert_organization(org, ES)
                for org in grid_data['institutes'] if org['status'] == 'active'
            ]
            with open(ROR_DUMP['ROR_JSON_PATH'], 'w') as outfile:
                json.dump(ror_data, outfile, indent=4)
            self.stdout.write('ROR dataset created')

        # generate zip archive
        with zipfile.ZipFile(ROR_DUMP['ROR_ZIP_PATH'], 'w') as zipArchive:
            zipArchive.write(ROR_DUMP['ROR_JSON_PATH'],
                             arcname='ror.json',
                             compress_type=zipfile.ZIP_DEFLATED)
            self.stdout.write('ROR dataset ZIP archive created')
