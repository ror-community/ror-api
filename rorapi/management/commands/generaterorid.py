import base32_crockford
import json
import os.path
import random
from .createindex import Command as CreateIndexCommand
from rorapi.settings import ES, ES7, ES_VARS, ROR_API, GRID_REMOVED_IDS

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


def check_ror_id(enable_es_7):
    """Checks if generated ror id exists in the index. If so, it generates a new id, otherwise it returns the generated ror id
    """
    ror_id = generate_ror_id()
    if enable_es_7:
        s = ES7.search(ES_VARS['INDEX'],
                        body={'query': {
                            'term': {
                                '_id': ror_id
                                }}})
        if s['hits']['total']['value'] == 1 or s in GRID_REMOVED_IDS:
            check_ror_id(enable_es_7)
    else:
        s = ES.search(ES_VARS['INDEX'],
                        body={'query': {
                            'term': {
                                '_id': ror_id
                                }}})
        if s['hits']['total'] == 1 or s in GRID_REMOVED_IDS:
            check_ror_id(enable_es_7)
    return ror_id

