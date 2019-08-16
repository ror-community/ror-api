from .settings import ES, ES_VARS

from elasticsearch_dsl import Search, Q


class ESQueryBuilder():
    """Elasticsearch query builder class"""
    def __init__(self):
        self.search = Search(using=ES, index=ES_VARS['INDEX'])

    def add_id_query(self, id):
        self.search = self.search.query('match',
                                        id={
                                            'query': id,
                                            'operator': 'and'
                                        })

    def add_match_all_query(self):
        self.search = self.search.query('match_all')

    def add_string_query(self, terms):
        self.search = self.search.query('query_string',
                                        query=terms,
                                        fuzzy_max_expansions=1)

    def add_phrase_query(self, fields, terms):
        self.search.query = Q(
            'dis_max',
            queries=[Q('match_phrase', **{f: terms}) for f in fields])

    def add_common_query(self, fields, terms):
        self.search.query = Q(
            'dis_max',
            queries=[
                Q('common', **{f: {
                    'query': terms,
                    'cutoff_frequency': 0.001
                }}) for f in fields
            ])

    def add_match_query(self, terms):
        self.search = self.search.query('match', acronyms=terms)

    def add_fuzzy_query(self, fields, terms):
        self.search.query = Q(
            'dis_max',
            queries=[
                Q('match', **{f: {
                    'query': terms,
                    'fuzziness': 'AUTO'
                }}) for f in fields
            ])

    def add_filters(self, filters):
        for f, v in filters:
            self.search = self.search.filter('term', **{f: v})

    def add_aggregations(self, names):
        for name in names:
            self.search.aggs.bucket(name[0],
                                    'terms',
                                    field=name[1],
                                    size=10,
                                    min_doc_count=1)

    def paginate(self, page):
        self.search = self.search[((page - 1) * ES_VARS['BATCH_SIZE']):(
            page * ES_VARS['BATCH_SIZE'])]

    def get_query(self):
        return self.search
