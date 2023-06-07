import base32_crockford
import random
from rorapi.queries import retrieve_organization, get_ror_id
from rorapi.settings import ROR_API

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


def check_ror_id():
    """Checks if generated ror id exists in the index. If so, it generates a new id, otherwise it returns the generated ror id
    """
    ror_id = get_ror_id(generate_ror_id())
    errors, organization = retrieve_organization(ror_id)
    if errors is None:
        check_ror_id()
    return ror_id

