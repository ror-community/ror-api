import re
import json
from titlecase import titlecase
from collections import defaultdict

from .matching import match_affiliation
from .models import Organization, ListResult, MatchingResult, Errors
from .settings import GRID_REMOVED_IDS, ROR_API, ES_VARS
from .es_utils import ESQueryBuilder

from urllib.parse import unquote

ALLOWED_FILTERS = ('country.country_code', 'types', 'country.country_name', 'status')
ALLOWED_PARAM_KEYS = ('query', 'page', 'filter', 'query.advanced', 'all_status')
ALLOWED_ALL_STATUS_VALUES = ('', 'true', 'false')
ALLOWED_FIELDS = ('acronyms', 'addresses.city', 'addresses.country_geonames_id',
    'addresses.geonames_city.city', 'addresses.geonames_city.geonames_admin1.ascii_name',
    'addresses.geonames_city.geonames_admin1.code', 'addresses.geonames_city.geonames_admin1.name',
    'addresses.geonames_city.geonames_admin2.ascii_name', 'addresses.geonames_city.geonames_admin2.code',
    'addresses.geonames_city.geonames_admin2.name', 'addresses.geonames_city.id', 'addresses.geonames_city.license.attribution',
    'addresses.geonames_city.license.license', 'addresses.geonames_city.nuts_level1.code',
    'addresses.geonames_city.nuts_level1.name', 'addresses.geonames_city.nuts_level2.code',
    'addresses.geonames_city.nuts_level2.name', 'addresses.geonames_city.nuts_level3.code',
    'addresses.geonames_city.nuts_level3.name', 'addresses.lat', 'addresses.line', 'addresses.lng',
    'addresses.postcode', 'addresses.primary', 'addresses.state', 'addresses.state_code', 'aliases',
    'country.country_code', 'country.country_name', 'email_address', 'established', 'external_ids.CNRS.all',
    'external_ids.CNRS.preferred', 'external_ids.Fundref.all', 'external_ids.Fundref.preferred', 'external_ids.HESA.all',
    'external_ids.HESA.preferred', 'external_ids.GRID.all', 'external_ids.GRID.preferred', 'external_ids.ISNI.all',
    'external_ids.ISNI.preferred', 'external_ids.OrgRef.all', 'external_ids.OrgRef.preferred', 'external_ids.UCAS.all',
    'external_ids.UCAS.preferred', 'external_ids.UKPRNS.all', 'external_ids.UKPRNS.preferred', 'external_ids.Wikidata.all',
    'external_ids.Wikidata.preferred', 'id', 'ip_addresses', 'labels.iso639', 'labels.label', 'links', 'name',
    'relationships.id', 'relationships.label', 'relationships.type', 'status', 'types', 'wikipedia_url')
# Values that are not valid field names that can precede : char
# \: escaped :
# \*: match subfields, ex addresses.\*:
# _exists_: check if field has non-null value, ex _exists_:wikipedia_url
ALLOWED_ENDINGS = ('_exists_', '\\', '\\*')

def get_ror_id(string):
    """Extracts ROR id from a string and transforms it into canonical form"""

    m = re.match(r'^(?:(?:(?:http|https):\/\/)?ror\.org\/)?(0\w{6}\d{2})$',
                 unquote(string))
    if m is not None:
        return ROR_API['ID_PREFIX'] + m.group(1)
    return None

def adv_query_string_to_list(query_string):
    field_list = []
    if ':' in query_string:
        query_string = query_string.replace(':', ':SPLIT_HERE')
        query_split = query_string.split('SPLIT_HERE')
        for substr in query_split:
            if substr.endswith(':'):
                field_list.append(substr.rstrip(':'))
    return field_list

def check_status_adv_q(adv_q_string):
    status_in_q = False
    adv_query_fields = adv_query_string_to_list(adv_q_string)
    status_fields = [
        f for f in adv_query_fields if f.endswith('status')
    ]
    if len(status_fields) > 0:
        status_in_q = True
    return status_in_q

def filter_string_to_list(filter_string):
    filter_list = []
    # some country names contain comma chars
    # allow comma chars in country_name filter values only
    # country.country_name:Germany,types:Company
    if 'country.country_name' in filter_string:
        country_name_filters = []
        search = re.findall('country.country_name:([^:]*)', filter_string)
        if search:
            for s in search:
                if len(re.findall(",", s)) > 1:
                    s = s.rsplit(",", 1)[0]
                for allowed_filter in ALLOWED_FILTERS:
                    if allowed_filter in s:
                        s = s.rsplit("," + allowed_filter, 1)[0]
                country_name_filter = 'country.country_name:' + s
                country_name_filters.append(country_name_filter)
                filter_string = filter_string.replace(country_name_filter, '')
        filter_list = [f for f in filter_string.split(',') if f]
        filter_list = filter_list + country_name_filters
    else:
        filter_list = [f for f in filter_string.split(',') if f]
    return filter_list

def validate(params):
    """Validates API GET parameters. Returns an error object
    that can be serialized into JSON or None."""

    illegal_names = [
        k for k in params.keys() if k not in ALLOWED_PARAM_KEYS
    ]
    errors = [
        'query parameter \'{}\' is illegal'.format(n) for n in illegal_names
    ]

    if not illegal_names:
        if 'all_status' in params.keys():
            if str(params.get('all_status')).lower() not in ALLOWED_ALL_STATUS_VALUES:
                errors.extend([
                'allowed values for all_status parameter are empty (no value), true or false'
            ])
        if len(params.keys()) > 1:
            if 'query' in  params.keys() and 'query.advanced' in  params.keys():
                errors.extend([
                    'query and query.advanced parameters cannot be combined. please use either query OR query.advanced'
                ])

    adv_query_fields = adv_query_string_to_list(params.get('query.advanced', ''))
    illegal_fields = [
        f for f in adv_query_fields if (not f.endswith(tuple(ALLOWED_FIELDS)) and not f.endswith(tuple(ALLOWED_ENDINGS)))
    ]
    errors.extend([
        'string \'{}\' contains an illegal field name'.format(f) for f in illegal_fields])

    filters = filter_string_to_list(params.get('filter', ''))
    invalid_filters = [f for f in filters if ':' not in f]
    errors.extend([
        'filter \'{}\' is not in the key:value form'.format(n) for n in invalid_filters])

    valid_filters = [f for f in filters if ':' in f]
    filter_keys = [f.split(':')[0] for f in valid_filters]
    illegal_keys = [
        v for v in filter_keys
        if v not in ALLOWED_FILTERS
    ]
    errors.extend([
        'filter key \'{}\' is illegal'.format(k) for k in illegal_keys])

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
    ror_id = None

    if 'all_status' in params:
        if params['all_status'].lower() == "false":
            del params['all_status']

    if 'query.advanced' in params:
        qb.add_string_query_advanced(params.get('query.advanced'))
    elif 'query' in params:
        ror_id = get_ror_id(params.get('query'))
        if ror_id is not None:
            qb.add_id_query(ror_id)
        else:
            qb.add_string_query(params.get('query'))
    else:
        qb.add_match_all_query()


    if 'filter' in params or (not 'all_status' in params):
        filters = [
            f.split(':') for f in filter_string_to_list(params.get('filter', '')) if f
        ]
        # normalize filter values based on casing conventions used in ROR records
        for f in filters:
            if f[0] == 'types':
                f[1] = f[1].title()
            if f[0] == 'country.country_code':
                f[1] = f[1].upper()
            if f[0] == 'country.country_name':
                f[1] = titlecase(f[1])
            if f[0] == 'status':
                f[1] = f[1].lower()
        filters = [(f[0], f[1]) for f in filters]

        filter_dict = {}
        temp = defaultdict(list)
        for k,v in filters:
            temp[k].append(v)
        filter_dict = dict((k, tuple(v)) for k, v in temp.items())

        if (not 'status' in filter_dict) and (not 'all_status' in params) and ror_id is None:
            status_in_adv_q = False
            if 'query.advanced' in params:
                status_in_adv_q = check_status_adv_q(params.get('query.advanced'))
            if not status_in_adv_q:
                filter_dict.update({'status': ['active']})
        qb.add_filters(filter_dict)

    qb.add_aggregations([('types', 'types'),
                         ('countries', 'country.country_code'), ('statuses', 'status')])

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
    if any(ror_id in ror_id_url for ror_id_url in GRID_REMOVED_IDS):
        return Errors(["ROR ID \'{}\' was removed by GRID during the time period (Jan 2019-Mar 2022) "
        "that ROR was synced with GRID. We are currently working with the ROR Curation Advisory Board "
        "to restore these records and expect to complete this work in 2022".format(ror_id)]), None
    search = build_retrieve_query(ror_id)
    results = search.execute()
    total = results.hits.total.value
    if total > 0:
        return None, Organization(results[0])
    return Errors(['ROR ID \'{}\' does not exist'.format(ror_id)]), None
