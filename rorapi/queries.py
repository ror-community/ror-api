import re

from .models import Organization, ListResult, Errors
from .settings import ES, ES_VARS, ROR_API

from elasticsearch_dsl import Search


class ESQueryBuilder():
    """Elasticsearch query builder class"""

    def __init__(self):
        self.search = Search(using=ES, index=ES_VARS['INDEX'])

    def add_id_query(self, id):
        self.search = self.search.query('match', id={'query': id,
                                                     'operator': 'and'})

    def add_match_all_query(self):
        self.search = self.search.query('match_all')

    def add_multi_match_query(self, fields, terms):
        self.search = self.search.query('multi_match', query=terms,
                                        operator='and', type='phrase_prefix',
                                        slop=3, max_expansions=10,
                                        fields=fields)

    def add_string_query(self, terms):
        terms = re.sub(r'([\+\-=\&\|><!\(\)\{\}\[\]\^"\~\*\?:\\\/])',
                       lambda m: '\\' + m.group(), terms)
        self.search = self.search.query('query_string', query=terms)

    def add_name_query(self, terms):
        self.search = self.search.query('match', name={'query': terms,
                                                       'operator': 'and'})

    def add_filters(self, filters):
        for f, v in filters:
            self.search = self.search.filter('term', **{f: v})

    def add_aggregations(self, names):
        for name in names:
            self.search.aggs.bucket(name[0], 'terms', field=name[1], size=10,
                                    min_doc_count=1)

    def paginate(self, page):
        self.search = self.search[((page-1) * ES_VARS['BATCH_SIZE']):
                                  (page * ES_VARS['BATCH_SIZE'])]

    def get_query(self):
        return self.search


def get_ror_id(string):
    """Extracts ROR id from a string and transforms it into canonical form"""

    m = re.match(r'^(?:(?:http|https):\/\/)?(?:ror\.org\/)?(0\w{6}\d{2})$',
                 string)
    if m is not None:
        return ROR_API['ID_PREFIX'] + m.group(1)
    return None


def validate(params):
    """Validates API GET parameters. Returns an error object
    that can be serialized into JSON or None."""

    illegal_names = [k for k in params.keys()
                     if k not in ['query', 'page', 'filter', 'query.name',
                                  'query.names', 'query.ui']]
    errors = ['query parameter \'{}\' is illegal'.format(n)
              for n in illegal_names]

    filters = [f for f in params.get('filter', '').split(',') if f]
    invalid_filters = [f for f in filters if ':' not in f]
    errors.extend(['filter \'{}\' is not in the key:value form'.format(n)
                   for n in invalid_filters])

    valid_filters = [f for f in filters if ':' in f]
    filter_keys = [f.split(':')[0] for f in valid_filters]
    illegal_keys = [v for v in filter_keys
                    if v not in ['country.country_code', 'types',
                                 'country.country_name']]
    errors.extend(['filter key \'{}\' is illegal'.format(k)
                   for k in illegal_keys])

    if 'page' in params:
        try:
            int(params.get('page'))
        except ValueError:
            errors.append('page \'{}\' is not an integer'
                          .format(params.get('page')))

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
    elif 'query.name' in params:
        qb.add_name_query(params.get('query.name'))
    elif 'query.names' in params:
        qb.add_multi_match_query(
            ['name', 'aliases', 'acronyms', 'labels.label'],
            params.get('query.names'))
    elif 'query.ui' in params:
        qb.add_multi_match_query(
            ['_id^10', 'external_ids.GRID.all^10', 'external_ids.ISNI.all^10',
             'external_ids.FundRef.all^10', 'external_ids.Wikidata.all^10',
             'name^5', 'aliases^5', 'acronyms^5', 'labels.label^5', '_all'],
            params.get('query.ui'))
    else:
        qb.add_match_all_query()

    if 'filter' in params:
        filters = [f.split(':')
                   for f in params.get('filter', '').split(',') if f]
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
