from rorapi.settings import ES7, ES_VARS

from elasticsearch_dsl import Search, Q


class ESQueryBuilder:
    """Elasticsearch query builder class"""

    def __init__(self, version):
        if version == "v2":
            self.search = Search(using=ES7, index=ES_VARS["INDEX_V2"])
        else:
            self.search = Search(using=ES7, index=ES_VARS["INDEX_V1"])
        self.search = self.search.extra(track_total_hits=True)
        self.search = self.search.params(search_type="dfs_query_then_fetch")

    def add_id_query(self, id):
        self.search = self.search.query("match", id={"query": id, "operator": "and"})

    def add_match_all_query(self):
        self.search = self.search.query("match_all")

    def add_string_query(self, terms):
        self.search = self.search.query(
            "nested",
            path="names_ids",
            score_mode="max",
            query=Q("query_string", query=terms, fuzzy_max_expansions=1),
        )

    def add_affiliation_query(self, terms, max_candidates):
        # print(terms)
        self.search = self.search.query(
            "nested",
            path="affiliation_match.names",
            score_mode="max",
            query=Q("match", **{"affiliation_match.names.name": terms})
        ).extra(size=max_candidates)

        '''
        Nested(
        path="outer_nested_field",
        query=Q(
            "nested",
            path="outer_nested_field.inner_nested_field",
            query=Q("match", outer_nested_field__inner_nested_field__some_field="some_value")
        )
        '''

    def add_string_query_advanced(self, terms):
        self.search = self.search.query(
            "bool",
            must=Q(
                "query_string",
                query=terms,
                default_field="*",
                default_operator="and",
                fuzzy_max_expansions=1,
            ),
        )

    def add_phrase_query(self, fields, terms):
        self.search.query = Q(
            "dis_max", queries=[Q("match_phrase", **{f: terms}) for f in fields]
        )

    def add_common_query(self, fields, terms):
        self.search.query = Q(
            "dis_max",
            queries=[
                Q("common", **{f: {"query": terms, "cutoff_frequency": 0.001}})
                for f in fields
            ],
        )

    def add_match_query(self, terms):
        self.search = self.search.query("match", acronyms=terms)

    def add_fuzzy_query(self, fields, terms):
        self.search.query = Q(
            "dis_max",
            queries=[
                Q("match", **{f: {"query": terms, "fuzziness": "AUTO"}}) for f in fields
            ],
        )

    def add_filters(self, filters):
        for f, v in filters.items():
            self.search = self.search.filter("terms", **{f: v})

    def add_aggregations(self, names):
        for name in names:
            self.search.aggs.bucket(
                name[0], "terms", field=name[1], size=10, min_doc_count=1
            )

    def paginate(self, page):
        self.search = self.search[
            ((page - 1) * ES_VARS["BATCH_SIZE"]) : (page * ES_VARS["BATCH_SIZE"])
        ]

    def get_query(self):
        return self.search
 
    def add_sort(self, field, order="asc"):
        self.search = self.search.sort({field: {"order": order}})