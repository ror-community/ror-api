import re
from titlecase import titlecase

from .matching import match_affiliation
from .models import Organization, ListResult, MatchingResult, Errors
from .settings import ROR_API, ES_VARS
from .es_utils import ESQueryBuilder

from urllib.parse import unquote

ALLOWED_FILTERS = ['country.country_code', 'types', 'country.country_name']


def get_ror_id(string):
    """Extracts ROR id from a string and transforms it into canonical form"""

    m = re.match(r'^(?:(?:(?:http|https):\/\/)?ror\.org\/)?(0\w{6}\d{2})$',
                 unquote(string))
    if m is not None:
        return ROR_API['ID_PREFIX'] + m.group(1)
    return None

def filter_string_to_list(filter_string):
    filter_list = []
    for f in ALLOWED_FILTERS:
        if f in filter_string:
            key = f
            value = ''
            # some country names contain , chars
            # so can't split filters using ,
            # need to check between filter names for values
            for y in ALLOWED_FILTERS:
                search_between_filter_names = re.search(f + '(.*)' + y, filter_string)
                if search_between_filter_names:
                    value = search_between_filter_names.group(1).rstrip(",")
            if not value:
                search_between_filter_name_end = re.search(f + '(.*$)', filter_string)
                value = search_between_filter_name_end.group(1).rstrip(",")
            # normalize filter values based on casing conventions used in ROR records
            if value:
                if f == 'types':
                    value = value.title()
                if f == 'country.country_code':
                    value =  value.upper()
                if f == 'country.country_name':
                    value = titlecase(value)
            filter_list.append(key + value)
    return filter_list

def validate(params):
    """Validates API GET parameters. Returns an error object
    that can be serialized into JSON or None."""

    illegal_names = [
        k for k in params.keys() if k not in ['query', 'page', 'filter']
    ]
    errors = [
        'query parameter \'{}\' is illegal'.format(n) for n in illegal_names
    ]
    filters = filter_string_to_list(params.get('filter', ''))
    invalid_filters = [f for f in filters if ':' not in f]
    errors.extend([
        'filter \'{}\' is not in the key:value form'.format(n)
        for n in invalid_filters
    ])

    valid_filters = [f for f in filters if ':' in f]
    filter_keys = [f.split(':')[0] for f in valid_filters]
    illegal_keys = [
        v for v in filter_keys
        if v not in ALLOWED_FILTERS
    ]
    errors.extend(
        ['filter key \'{}\' is illegal'.format(k) for k in illegal_keys])

    if 'page' in params:
        page = params.get('page')
        try:
            page = int(page)
            if page < 1 or page > ES_VARS['MAX_PAGE']:
                errors.append('page \'{}\' outside of range {}-{}'.format(
                    page, 1, ES_VARS['MAX_PAGE']))
        except ValueError:
            errors.append('page \'{}\' is not an integer'.format(page))

    return Errors(errors) if errors else None


def build_search_query(params):
    """Builds search query from API parameters"""

    qb = ESQueryBuilder()

    if 'query' in params:
        ror_id = get_ror_id(params.get('query'))
        if ror_id is not None:
            qb.add_id_query(ror_id)
        else:
            qb.add_string_query(params.get('query'))
    else:
        qb.add_match_all_query()

    if 'filter' in params:
        filters = [
            f.split(':') for f in filter_string_to_list(params.get('filter', '')) if f
        ]
        filters = [(f[0], f[1]) for f in filters]
        qb.add_filters(filters)

    qb.add_aggregations([('types', 'types'),
                         ('countries', 'country.country_code')])

    qb.paginate(int(params.get('page', 1)))

    return qb.get_query()


def build_retrieve_query(ror_id):
    """Builds retrieval query"""

    qb = ESQueryBuilder()
    qb.add_id_query(ror_id)
    return qb.get_query()


def search_organizations(params):
    """Searches for organizations according to the parameters"""

    error = validate(params)
    if error is not None:
        return error, None

    search = build_search_query(params)
    return None, ListResult(search.execute())


def retrieve_organization(ror_id):
    """Retrieves the organization of the given ROR ID"""

    search = build_retrieve_query(ror_id)
    results = search.execute()
    if results.hits.total > 0:
        return None, Organization(results[0])
    return Errors(['ROR ID \'{}\' does not exist'.format(ror_id)]), None
