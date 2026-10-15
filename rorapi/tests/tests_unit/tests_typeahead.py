import re
import unicodedata

from django.test import SimpleTestCase

from rorapi.common import typeahead
from rorapi.v2.index_template import index_template

from .utils import scored_tiers

LONGEST_NAME = ('Всероссийский научно-исследовательский институт по осушению месторождений полезных ископаемых, '
                'защите инженерных сооружений от обводнения, специальным горным работам, геомеханике, геофизике, '
                'гидротехнике, геологии и маркшейдерскому делу')


LONG_HAN = ''.join(chr(0x4E00 + i) for i in range(300))
# Han (3 bytes) alternating with CJK Extension B (4 bytes): 777 UTF-8 bytes in fewer code points than
# LONGEST_NAME has.
HAN_AND_EXTENSION_B = ''.join(chr(0x4E00 + i) + chr(0x20000 + i) for i in range(111))

LUCENE_MAX_PREFIX_BYTES = 1000
# A lone surrogate left by a cut inside a pair encodes as U+FFFD, three bytes like any BMP unit.
MAX_UTF8_BYTES_PER_UTF16_UNIT = 3
# Plain AUTO is AUTO:3,6, one edit from 3 code points and two from 6.
ES_AUTO_FUZZINESS_LENGTHS = (3, 6)
TYPEAHEAD_TOKEN_LIMIT = 64

# Token counts recorded from ES 7.10.1 _analyze with typeahead_char_search (the standard tokenizer).
ES_TOKEN_COUNTS = {
    '北京大学': 4,
    'とうきょうだいがく': 9,
    'コンピューター': 1,
    'トヨタ自動車': 4,
    'aカaカ': 4,
    '2024年東京': 4,
    'LG전자2024': 1,
    '人々': 2,
    '東\u0301京': 2,
    'Montre\u0301al': 1,
    'ภาษาไทย': 1,
    '東京・大学': 4,
    'らーめん': 4,
    'Harvard University': 2,
    "Hawai'i Hilo": 2,
    'Children\u2019s Hospital': 2,
    'O`Reilly': 1,
    'Hawai\u00b4i': 1,
    "rock 'n' roll": 3,
    "'s-Hertogenbosch": 2,
    "\u6771\u4eac'\u5927\u5b66": 4,
    'Fed\u00ader\u00adal Of\u00adfice of Ad\u00admin\u00adis\u00adtra\u00adtion': 4,
    '\u0dc1\u0dca\u200d\u0dbb\u0dd3 \u0dbd\u0d82\u0d9a\u0dcf': 2,
    '\u0634\u0631\u06a9\u062a\u200c\u0647\u0627': 1,
    'zero\u200bwidth': 2,
}

# Token counts recorded from ES 7.10.1 _analyze with typeahead_fuzzy_search's filters through
# typeahead_cjk_bigram, before its limit.
ES_PAIRED_TOKEN_COUNTS = {
    '自然科学研究機構アストロバイオロジーセソ': 8,
    '北京大学': 3,
    'とうきょうだいがく': 8,
    'トヨタ自動車': 3,
    '2024年東京': 3,
    '佐々木': 3,
    '東京\u00ad大学': 3,
    '東\u0301京': 1,
    "東京'大学": 2,
    '東京・大学': 2,
    'らーめん': 3,
}

TWO_SET_KEYS = {
    '가': 'ㄱㅏ', '힣': 'ㅎㅣㅎ', '서': 'ㅅㅓ', '울': 'ㅇㅜㄹ', '핚': 'ㅎㅏㄱㄱ', '괗': 'ㄱㅗㅏㅎ', '쀍': 'ㅂㅂㅜㅔㄹㄱ',
    '읭': 'ㅇㅡㅣㅇ', '앉': 'ㅇㅏㄴㅈ', '없': 'ㅇㅓㅂㅅ', 'ㅘ': 'ㅗㅏ', 'ㄲ': 'ㄱㄱ', 'ㄳ': 'ㄱㅅ', 'ㅢ': 'ㅡㅣ',
}

NFC_SAMPLES = {
    'Centre Me\u0301dical': 'Centre M\u00e9dical',
    '\u0c95\u0cc6\u0cd5': '\u0c95\u0cc7',
    '\u09df': '\u09af\u09bc',
    'I\u0307l': '\u0130l',
}


def longest_match(rules, text):
    longest = max(map(len, rules), default=0)
    out, at = [], 0
    while at < len(text):
        n = next((n for n in range(longest, 0, -1) if text[at:at + n] in rules), 0)
        out.append(rules[text[at:at + n]] if n else text[at])
        at += n or 1
    return ''.join(out)


BOOL_OCCURRENCES = ('filter', 'must', 'must_not', 'should')


def walk(value, occurrence=None):
    if isinstance(value, dict):
        for kind, inner in value.items():
            if isinstance(inner, dict):
                for field, body in inner.items():
                    yield occurrence, kind, field, body
            yield from walk(inner, kind if kind in BOOL_OCCURRENCES else occurrence)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item, occurrence)


def clauses_on(value, field):
    return [(kind, body) for _, kind, on, body in walk(value) if on == field]


def query_text(raw):
    [(_, text)] = clauses_on(typeahead.text_query(typeahead.clean(raw)).to_dict(), 'names_ids.id')
    return text


def clauses_needed(minimum_should_match, clauses):
    """Clauses a match with minimum_should_match "a<-b" needs out of `clauses`: all up to a, all but b above a."""
    at_most, missing = (int(v) for v in minimum_should_match.split('<-'))
    return clauses if clauses <= at_most else clauses - missing


def most_edits(fuzziness, longest):
    kind, _, lengths = str(fuzziness).upper().partition(':')
    if kind != 'AUTO':
        return int(kind)
    low, high = map(int, lengths.split(',')) if lengths else ES_AUTO_FUZZINESS_LENGTHS
    return 0 if longest < low else 1 if longest < high else 2


def ordered_tiers(text):
    return [(boost, f.to_dict()) for boost, f in typeahead.tiers(text)
            if any(kind == 'intervals' for kind, _ in clauses_on(f.to_dict(), 'names_ids.name.edge'))]


def ordered_match(tier):
    [body] = [body for kind, body in clauses_on(tier, 'names_ids.name.edge') if kind == 'intervals']
    return body['match']


def typo_boosts(text, field):
    return [boost for boost, f in typeahead.tiers(text)
            if any(isinstance(body, dict) and 'fuzziness' in body for _, body in clauses_on(f.to_dict(), field))]


class TokensTestCase(SimpleTestCase):

    def test_counts_what_the_standard_tokenizer_emits(self):
        for text, count in ES_TOKEN_COUNTS.items():
            self.assertEqual(typeahead._token_count(text), count, text)


class NameRankTestCase(SimpleTestCase):

    def rank(self, value, *types):
        return typeahead.name_rank({'value': value, 'types': list(types)})

    def label_rank(self, words):
        return self.rank(' '.join(['word'] * words), 'label')

    def test_a_name_typed_as_an_acronym_too_ranks_as_its_full_name_kind(self):
        for value, types in [('ISEG', ['ror_display', 'label']), ('BASA', ['label']), ('IESE', ['alias'])]:
            with self.subTest(value=value, types=types):
                self.assertEqual(self.rank(value, 'acronym', *types), self.rank(value, *types))

    def test_display_name_beats_a_label_with_as_many_words(self):
        self.assertLess(self.rank('University of Lisbon', 'ror_display', 'label'),
                        self.rank('Universidade de Lisboa', 'label'))

    def test_fewer_words_rank_first_within_a_kind(self):
        self.assertLess(self.rank('Universität Wien', 'label'),
                        self.rank('University of Vienna', 'ror_display', 'label'))

    def test_kind_before_word_count(self):
        self.assertLess(self.label_rank(99), self.rank('Harvard', 'alias'))
        self.assertLess(self.rank('Harvard', 'alias'), self.rank('HU', 'acronym'))

    def test_caps_the_word_count_at_99(self):
        self.assertEqual(self.rank(' '.join(['word'] * 150), 'alias'), self.rank(' '.join(['word'] * 99), 'alias'))

    def test_han_and_kana_names_rank_by_token_count(self):
        self.assertEqual(self.rank('東京大学', 'label'), self.label_rank(4))
        self.assertEqual(self.rank('東京医科大学', 'label'), self.label_rank(6))
        self.assertEqual(self.rank('東京都立病院機構', 'label'), self.label_rank(8))
        self.assertEqual(self.rank('トヨタ自動車', 'label'), self.label_rank(4))
        self.assertEqual(self.rank('とうきょうだいがく', 'label'), self.label_rank(9))

    def test_mixed_script_names_rank_by_token_count(self):
        self.assertEqual(self.rank('Kyoto Robotics株式会社', 'label'), self.label_rank(6))
        self.assertEqual(self.rank('NTT東日本関東病院', 'label'), self.label_rank(8))
        self.assertEqual(self.rank('CNRS-産総研ロボット工学連携研究室', 'label'), self.label_rank(12))
        self.assertEqual(self.rank('有限会社 HREM', 'label'), self.label_rank(5))
        self.assertEqual(self.rank('中国人民解放军第三0五医院', 'label'), self.label_rank(13))

    def test_names_in_other_scripts_keep_their_word_count(self):
        self.assertEqual(self.rank('서울대학교 병원', 'label'), self.label_rank(2))
        self.assertEqual(self.rank('हिन्दी विश्वविद्यालय', 'label'), self.label_rank(2))

    def test_fewer_tokens_rank_first_whatever_the_scripts(self):
        pairs = [
            ('三菱アルミニウム', '三菱FBRシステムズ株式会社'),
            ('JFE Holdings (Japan)', 'JFEスチール株式会社'),
            ('中国人民解放军第四五八', '中国人民解放军第三0五医院'),
        ]
        for shorter, longer in pairs:
            with self.subTest(shorter=shorter, longer=longer):
                self.assertLess(self.rank(shorter, 'label'), self.rank(longer, 'label'))

    def test_counts_apostrophe_parts_and_joins_format_characters(self):
        federal_office = 'Fed\u00ader\u00adal Of\u00adfice of Ad\u00admin\u00adis\u00adtra\u00adtion'
        self.assertEqual(self.rank(federal_office, 'label'), self.label_rank(4))
        sri_lanka = '\u0dc1\u0dca\u200d\u0dbb\u0dd3 \u0dbd\u0d82\u0d9a\u0dcf'
        self.assertEqual(self.rank(sri_lanka, 'label'), self.label_rank(2))
        self.assertEqual(self.rank("Children's Hospital", 'label'), self.label_rank(3))
        self.assertEqual(self.rank('Children\u2019s Hospital', 'label'), self.label_rank(3))
        self.assertEqual(self.rank("Université d'Orléans", 'label'), self.label_rank(3))
        self.assertEqual(self.rank('Hawai\u02bbi', 'label'), self.label_rank(1))

    def test_every_name_rank_fits_under_the_tier_scale(self):
        worst = max(typeahead.name_rank({'value': ' '.join(['word'] * 200), 'types': [kind]})
                    for kind in ['acronym', 'alias', 'label'])
        self.assertLess(worst, typeahead._TIER_SCALE)


class RequiredWordsTestCase(SimpleTestCase):

    def test_drops_optional_words(self):
        self.assertEqual(typeahead.required_words('The University of Michigan'), 'University Michigan')
        self.assertEqual(typeahead.required_words('univ of mich'), 'univ mich')
        self.assertEqual(typeahead.required_words('Funai Electric Co.'), 'Funai Electric')
        self.assertEqual(typeahead.required_words('U.S. Department of Energy'), 'U S Department Energy')

    def test_all_optional_keeps_all(self):
        self.assertEqual(typeahead.required_words('the'), 'the')
        self.assertEqual(typeahead.required_words('Für'), 'Für')
        self.assertEqual(typeahead.required_words('de la'), 'de la')
        self.assertEqual(typeahead.required_words('Co'), 'Co')

    def test_unicode_words(self):
        self.assertEqual(typeahead.required_words("Université d'Orl"), "Université d'Orl")
        self.assertEqual(typeahead.required_words('हिन्दी'), 'हिन्दी')
        self.assertEqual(typeahead.required_words('東京大'), '東京大')

    def test_keeps_a_word_whole_around_an_apostrophe_or_a_format_character(self):
        self.assertEqual(typeahead.required_words("Hawai'i Hilo"), "Hawai'i Hilo")
        self.assertEqual(typeahead.required_words('Children\u2019s Hospital'), 'Children\u2019s Hospital')
        self.assertEqual(typeahead.required_words('Fed\u00ader\u00adal Office'), 'Fed\u00ader\u00adal Office')
        self.assertEqual(typeahead.required_words('zero\u200bwidth'), 'zero width')


class TypedWordsTestCase(SimpleTestCase):

    def test_keeps_an_unfinished_optional_last_word(self):
        self.assertEqual(typeahead.typed_words('Univ of A'), 'Univ A')
        self.assertEqual(typeahead.typed_words('Planck In'), 'Planck In')
        self.assertEqual(typeahead.typed_words('Fuji Electric Co'), 'Fuji Electric Co')
        self.assertEqual(typeahead.typed_words('The University of'), 'University of')

    def test_drops_a_finished_optional_last_word(self):
        self.assertEqual(typeahead.typed_words('Funai Electric Co.'), 'Funai Electric')
        self.assertEqual(typeahead.typed_words('Kobe Steel, Ltd.'), 'Kobe Steel')
        self.assertEqual(typeahead.typed_words('Fuji Electric Co, Ltd.'), 'Fuji Electric')

    def test_equals_required_words_otherwise(self):
        for text in ['The University of Michigan', 'univ of mich', 'de la', 'Co', 'de la Univ', '東京大',
                     "Université d'Orl", 'U.S. Department of Energy']:
            self.assertEqual(typeahead.typed_words(text), typeahead.required_words(text), text)

    def test_keeps_a_word_whole_around_an_apostrophe_or_a_format_character(self):
        self.assertEqual(typeahead.typed_words("Hawai'i Hilo"), "Hawai'i Hilo")
        self.assertEqual(typeahead.typed_words('Children\u2019s'), 'Children\u2019s')
        self.assertEqual(typeahead.typed_words('Fed\u00ader\u00adal'), 'Fed\u00ader\u00adal')
        self.assertEqual(typeahead.typed_words('zero\u200bwidth'), 'zero width')


class ValidationErrorsTestCase(SimpleTestCase):

    def test_rejects_input_without_letters_or_digits(self):
        for raw in ['**', '   ', '', '-', '\u0301', "'", '\u2019\u2019', '\u00ad', '\u200d', "' \u00ad"]:
            self.assertEqual(len(typeahead.validation_errors(raw)), 1, raw)

    def test_accepts_usable_input(self):
        for raw in ['a', 'Harv', '7', 'Université d\'Orl', '東京大', LONGEST_NAME, 'a' * 5000, 'word ' * 2000]:
            self.assertEqual(typeahead.validation_errors(raw), [], raw[:40])


class TiersTestCase(SimpleTestCase):

    def test_boosts_strictly_decreasing(self):
        boosts = [boost for boost, _ in typeahead.tiers('univ of mich')]
        self.assertEqual(boosts, sorted(set(boosts), reverse=True))

    def test_every_exact_word_outranks_a_typo_and_a_typo_outranks_a_missing_word(self):
        for text in ['The University of Michigan', 'Gothnburg University']:
            exact, fuzzy, partial = [], [], []
            for boost, f in typeahead.tiers(text):
                bodies = [body for field in ('names_ids.name.exact', 'names_ids.name.edge')
                          for _, body in clauses_on(f.to_dict(), field) if isinstance(body, dict)]
                if any('fuzziness' in body for body in bodies):
                    fuzzy.append(boost)
                elif any('minimum_should_match' in body for body in bodies):
                    partial.append(boost)
                else:
                    exact.append(boost)
            with self.subTest(text=text):
                self.assertNotEqual(fuzzy, [], 'no tier forgives a typo')
                self.assertGreater(min(exact), max(fuzzy))
                self.assertGreater(min(fuzzy), max(partial))

    def test_whole_name_typo_tier_runs_for_the_longest_registry_name(self):
        self.assertNotEqual(typo_boosts(LONGEST_NAME, 'names_ids.name.exact'), [])

    def test_whole_name_typo_tier_skips_long_input_in_a_three_or_four_byte_script(self):
        for text in [LONG_HAN, HAN_AND_EXTENSION_B]:
            with self.subTest(code_points=len(text), utf8_bytes=len(text.encode())):
                self.assertEqual(typo_boosts(text, 'names_ids.name.exact'), [])

    def test_partial_tiers_never_below_half(self):
        partial = [f.to_dict()['match']['names_ids.name.edge']
                   for boost, f in typeahead.tiers('univ of mich') if boost < 50]
        self.assertNotEqual(partial, [])
        for p in partial:
            with self.subTest(minimum_should_match=p['minimum_should_match']):
                self.assertEqual([n for n in range(1, TYPEAHEAD_TOKEN_LIMIT + 1)
                                  if clauses_needed(p['minimum_should_match'], n) < (n + 1) // 2], [])

    def test_word_tiers_use_required_words(self):
        clauses = [(kind, body) for boost, f in typeahead.tiers('The University of Michigan') if boost <= 70
                   for kind, body in clauses_on(f.to_dict(), 'names_ids.name.edge')]
        queries = [body['match']['query'] if kind == 'intervals' else body['query'] for kind, body in clauses]
        self.assertEqual(set(queries), {'University Michigan'})
        self.assertIn('intervals', [kind for kind, _ in clauses])
        self.assertIn(True, ['fuzziness' in body for _, body in clauses])

    def test_ordered_tiers_keep_an_unfinished_last_word(self):
        ordered = sorted(((boost, ordered_match(tier)) for boost, tier in ordered_tiers('Planck In')),
                         key=lambda tier: tier[0], reverse=True)
        self.assertEqual([match['query'] for _, match in ordered], ['Planck In', 'Planck'])
        self.assertGreater(ordered[0][0], 70)
        typed, required = [{k: v for k, v in match.items() if k != 'query'} for _, match in ordered]
        self.assertEqual(typed, required)

    def test_exact_tiers_let_the_engine_analyze_the_text(self):
        for text in ['Harv', 'univ of mich', '東京大', 'Planck In', 'Funai Electric Co.']:
            exact = [(kind, body) for _, f in typeahead.tiers(text)
                     for kind, body in clauses_on(f.to_dict(), 'names_ids.name.exact')]
            with self.subTest(text=text):
                self.assertLessEqual({kind for kind, _ in exact}, {'match', 'match_bool_prefix'})
                self.assertEqual({body['query'] if isinstance(body, dict) else body for _, body in exact}, {text})

    def test_ordered_tiers_require_every_token_before_the_intervals(self):
        for text in ['Harv', 'Planck In', '東京大']:
            ordered = [tier for _, tier in ordered_tiers(text)]
            self.assertEqual(len(ordered), 2, text)
            for tier in ordered:
                self.assertEqual(list(tier), ['bool'], text)
                match, intervals = tier['bool']['filter']
                settings = intervals['intervals']['names_ids.name.edge']['match']
                self.assertEqual(match['match']['names_ids.name.edge'], {
                    'query': settings['query'], 'analyzer': settings['analyzer'], 'operator': 'and'}, text)

    def test_full_name_tiers_take_any_name_with_a_full_name_type(self):
        tiers = {boost: f.to_dict() for boost, f in typeahead.tiers('ISEG')}

        def type_clauses(boost):
            return [(occurrence, kind, sorted(types) if isinstance(types, list) else types)
                    for occurrence, kind, field, types in walk(tiers[boost]) if field == 'names_ids.types']

        for boost in (100, 58):
            with self.subTest(boost=boost):
                self.assertEqual(type_clauses(boost), [('filter', 'terms', ['alias', 'label', 'ror_display'])])
        self.assertEqual(type_clauses(90), [('filter', 'term', 'acronym')])

    def test_external_identifier_matches_at_top_tier(self):
        boost, top = typeahead.tiers('grid.38142.3c')[0]
        self.assertEqual(boost, 100)
        self.assertIn({'term': {'names_ids.id': 'grid.38142.3c'}},
                      top.to_dict()['bool']['should'])


class QueryTestCase(SimpleTestCase):

    def test_id_query_scores_only_the_identifier(self):
        query = typeahead.id_query('https://ror.org/03vek6s52').to_dict()
        text_query = typeahead.text_query('Harv').to_dict()
        self.assertEqual(scored_tiers(query), [(100, {'term': {'names_ids.id': 'https://ror.org/03vek6s52'}})])
        self.assertEqual({k: v for k, v in query['nested'].items() if k != 'query'},
                         {k: v for k, v in text_query['nested'].items() if k != 'query'})

    def test_identifier_tier_gets_the_whole_cleaned_text(self):
        self.assertEqual(query_text('  Montre\u0301al '), 'Montr\u00e9al')
        words = ', '.join('w{}'.format(i) for i in range(100))
        for text in [LONGEST_NAME, 'U.S. Department of Energy!', words, '大' * 333, 'aก' * 250, 'a' * 5000]:
            with self.subTest(text=text[:40]):
                self.assertEqual(query_text(text), text)


ROOT_FIELDS = frozenset((
    'acronyms', 'admin', 'admin.created', 'admin.created.date', 'admin.created.schema_version',
    'admin.last_modified', 'admin.last_modified.date', 'admin.last_modified.schema_version',
    'affiliation_match', 'affiliation_match.country', 'affiliation_match.id',
    'affiliation_match.names', 'affiliation_match.names.name', 'affiliation_match.primary',
    'affiliation_match.relationships', 'affiliation_match.relationships.id',
    'affiliation_match.relationships.type', 'affiliation_match.status', 'domains', 'established',
    'external_ids', 'external_ids.all', 'external_ids.preferred', 'external_ids.type', 'id',
    'links', 'links.type', 'links.value', 'locations', 'locations.geonames_details',
    'locations.geonames_details.continent_code', 'locations.geonames_details.continent_code.raw',
    'locations.geonames_details.continent_name', 'locations.geonames_details.country_code',
    'locations.geonames_details.country_code.raw', 'locations.geonames_details.country_name',
    'locations.geonames_details.country_subdivision_code',
    'locations.geonames_details.country_subdivision_name', 'locations.geonames_details.lat',
    'locations.geonames_details.lng', 'locations.geonames_details.name', 'locations.geonames_id',
    'names', 'names.lang', 'names.types', 'names.value', 'names.value.keyword', 'names.value.norm',
    'relationships', 'relationships.id', 'relationships.label', 'relationships.label.keyword',
    'relationships.label.norm', 'relationships.type', 'status', 'status.raw', 'types', 'types.raw',
))


def mapped_fields(properties, prefix=''):
    for name, mapping in properties.items():
        full = prefix + name
        yield full, mapping
        yield from mapped_fields(mapping.get('properties', {}), full + '.')
        yield from mapped_fields(mapping.get('fields', {}), full + '.')


def load_template():
    template = index_template()
    return template['settings']['analysis'], dict(mapped_fields(template['mappings']['properties']))


class TypeaheadFieldsTestCase(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.analysis, cls.mapped = load_template()

    def test_typeahead_adds_no_root_field(self):
        self.assertEqual(frozenset(f for f in self.mapped if f.split('.')[0] != 'names_ids'), ROOT_FIELDS,
                         'query.advanced searches root documents with query_string, whose `*` expansion, field '
                         'patterns and _exists_ reach every root field. A field only query.typeahead reads '
                         'belongs in names_ids, because query.advanced\'s root query cannot match a nested '
                         'field; a field the other routes must search changes ROOT_FIELDS on purpose.')

    def test_typeahead_analyzers_are_used_only_on_the_name_subfields(self):
        for full, mapping in self.mapped.items():
            for key in ('analyzer', 'search_analyzer'):
                if mapping.get(key, '').startswith('typeahead_'):
                    self.assertTrue(full.startswith('names_ids.name.'), (full, key, mapping[key]))

    def test_edge_search_analyzer_is_the_query_routes_analyzer(self):
        self.assertEqual(self.mapped['names_ids.name.edge']['search_analyzer'],
                         self.mapped['names_ids.name']['analyzer'])

    def test_every_edge_clause_names_its_analyzer(self):
        for text in ['Harvard Univ', '東京大', ' of '.join('w{}'.format(i) for i in range(9)), LONG_HAN]:
            for boost, f in typeahead.tiers(text):
                for kind, body in clauses_on(f.to_dict(), 'names_ids.name.edge'):
                    settings = body['match'] if kind == 'intervals' else body
                    with self.subTest(text=text[:20], boost=boost, kind=kind):
                        self.assertIn(settings.get('analyzer'), sorted(self.analysis['analyzer']))


class AnalyzerTestCase(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.analysis, cls.mapped = load_template()
        cls.exact = cls.mapped['names_ids.name.exact']
        cls.index_analyzer = cls.mapped['names_ids.name.edge']['analyzer']
        tier = next(f for boost, f in typeahead.tiers('Harvard Univ') if boost == 60)
        [(_, body)] = clauses_on(tier.to_dict(), 'names_ids.name.edge')
        cls.word_analyzer = body['analyzer']

    def filters_of_type(self, analyzer, filter_type):
        filters = self.analysis['filter']
        return [filters[n] for n in self.analysis['analyzer'][analyzer]['filter']
                if filters.get(n, {}).get('type') == filter_type]

    def filter_chain(self, analyzer):
        filters = self.analysis['filter']
        return [filters.get(n, {'type': n}) for n in self.analysis['analyzer'][analyzer]['filter']]

    def bigram_filters(self, analyzer):
        return self.filters_of_type(analyzer, 'cjk_bigram')

    def ordered_tier_analyzer(self):
        tier = next(f for boost, f in typeahead.tiers('東京大') if boost == 70)
        return ordered_match(tier.to_dict())['analyzer']

    def word_typo_analyzer(self):
        [analyzer] = {body['analyzer']
                      for _, f in typeahead.tiers('Gothnburg University')
                      for _, body in clauses_on(f.to_dict(), 'names_ids.name.edge')
                      if isinstance(body, dict) and 'fuzziness' in body}
        return analyzer

    def word_typo_token_limit(self):
        [limit] = self.filters_of_type(self.word_typo_analyzer(), 'limit')
        return limit['max_token_count']

    def mapping_rules(self, char_filter):
        mappings = self.analysis['char_filter'].get(char_filter, {}).get('mappings', [])
        return dict(rule.split(' => ') for rule in mappings)

    def test_word_tiers_spell_hangul_as_two_set_keystrokes(self):
        for analyzer in {self.index_analyzer, self.word_analyzer, self.ordered_tier_analyzer()}:
            self.assertIn('typeahead_hangul_keys', self.analysis['analyzer'][analyzer]['char_filter'], analyzer)
        rules = self.mapping_rules('typeahead_hangul_keys')
        for char, keys in TWO_SET_KEYS.items():
            with self.subTest(char=char):
                self.assertEqual(rules.get(char), keys)
        self.assertNotIn('ㅅ', rules)

    def test_whole_name_tiers_keep_syllables(self):
        self.assertNotIn('typeahead_hangul_keys', self.analysis['analyzer']['typeahead_compact']['char_filter'])

    def test_nfc_rules_compose_non_nfc_text_and_keep_nfc_text(self):
        rules = self.mapping_rules('typeahead_nfc')
        for raw, nfc in NFC_SAMPLES.items():
            with self.subTest(raw=raw):
                self.assertEqual(longest_match(rules, raw), nfc)
                self.assertEqual(longest_match(rules, nfc), nfc)

    def test_typeahead_analyzers_compose_to_nfc_first_and_the_query_analyzer_does_not(self):
        analyzers = {self.index_analyzer, self.word_analyzer, self.ordered_tier_analyzer(), self.word_typo_analyzer(),
                     self.exact['analyzer']}
        for analyzer in analyzers:
            with self.subTest(analyzer=analyzer):
                self.assertEqual(self.analysis['analyzer'][analyzer]['char_filter'][:1], ['typeahead_nfc'])
        query_analyzer = self.mapped['names_ids.name']['analyzer']
        self.assertNotIn(query_analyzer, analyzers)
        self.assertNotIn('char_filter', self.analysis['analyzer'][query_analyzer])

    def test_word_tiers_count_bigrams_and_the_ordered_tier_counts_characters(self):
        self.assertEqual(len(self.bigram_filters(self.word_analyzer)), 1)
        self.assertEqual(self.bigram_filters(self.ordered_tier_analyzer()), [])

    def test_word_tiers_count_a_repeated_word_once_and_the_ordered_tiers_count_each_copy(self):
        word_tiers, ordered = set(), set()
        for _, f in typeahead.tiers('University of Chinese Academy of Sciences'):
            clauses = clauses_on(f.to_dict(), 'names_ids.name.edge')
            in_order = any(kind == 'intervals' for kind, _ in clauses)
            for kind, body in clauses:
                settings = body['match'] if kind == 'intervals' else body
                (ordered if in_order else word_tiers).add(settings['analyzer'])
        self.assertNotEqual(word_tiers, set())
        self.assertNotEqual(ordered, set())
        for analyzer in word_tiers:
            *_, last = self.filter_chain(analyzer)
            with self.subTest(analyzer=analyzer):
                self.assertEqual(last['type'], 'unique', self.analysis['analyzer'][analyzer]['filter'])
                self.assertFalse(last.get('only_on_same_position', False))
        for analyzer in ordered:
            with self.subTest(analyzer=analyzer):
                self.assertNotIn('unique', [f['type'] for f in self.filter_chain(analyzer)])

    def test_index_keeps_characters_for_the_ordered_tier(self):
        [index_bigrams] = self.bigram_filters(self.index_analyzer)
        self.assertTrue(index_bigrams.get('output_unigrams'))
        self.assertEqual(index_bigrams['ignored_scripts'],
                         self.bigram_filters(self.word_analyzer)[0]['ignored_scripts'])

    def test_index_holds_each_term_once_per_position(self):
        *_, last = self.filter_chain(self.index_analyzer)
        self.assertEqual(last['type'], 'remove_duplicates', self.analysis['analyzer'][self.index_analyzer]['filter'])

    def test_word_and_ordered_tier_analyzers_cap_tokens_and_the_index_analyzer_does_not(self):
        for analyzer in {self.word_analyzer, self.ordered_tier_analyzer()}:
            limits = self.filters_of_type(analyzer, 'limit')
            self.assertEqual([f['max_token_count'] for f in limits], [TYPEAHEAD_TOKEN_LIMIT], analyzer)
        self.assertEqual(self.filters_of_type(self.index_analyzer, 'limit'), [])

    def test_word_typo_tiers_analyze_like_the_word_tiers_but_stop_at_fewer_tokens(self):
        analyzer = self.word_typo_analyzer()
        fuzzy, word = (self.analysis['analyzer'][a] for a in (analyzer, self.word_analyzer))
        self.assertEqual({k: v for k, v in fuzzy.items() if k != 'filter'},
                         {k: v for k, v in word.items() if k != 'filter'})

        def chain_apart_from_the_limit(name):
            return [f if f['type'] != 'limit' else 'limit' for f in self.filter_chain(name)]

        self.assertEqual(chain_apart_from_the_limit(analyzer), chain_apart_from_the_limit(self.word_analyzer))
        [limit], [word_limit] = (self.filters_of_type(a, 'limit') for a in (analyzer, self.word_analyzer))
        self.assertLess(limit['max_token_count'], word_limit['max_token_count'])

    def test_word_typo_tiers_stop_at_their_analyzer_limit_and_the_whole_name_typo_tier_does_not(self):
        limit = self.word_typo_token_limit()
        texts = {
            'latin': lambda tokens: ' of '.join('w{}'.format(i) for i in range(tokens)),
            # cjk_bigram pairs n + 1 Han characters into n tokens.
            'han': lambda tokens: ''.join(chr(0x4E00 + i) for i in range(tokens + 1)),
        }
        for script, text_of in texts.items():
            with self.subTest(script=script, tokens=limit):
                self.assertNotEqual(typo_boosts(text_of(limit), 'names_ids.name.edge'), [])
                self.assertNotEqual(typo_boosts(text_of(limit), 'names_ids.name.exact'), [])
            with self.subTest(script=script, tokens=limit + 1):
                self.assertEqual(typo_boosts(text_of(limit + 1), 'names_ids.name.edge'), [])
                self.assertNotEqual(typo_boosts(text_of(limit + 1), 'names_ids.name.exact'), [])

    def test_word_typo_tiers_run_while_the_analyzer_emits_at_most_its_limit_after_pairing(self):
        limit = self.word_typo_token_limit()
        for text, count in ES_PAIRED_TOKEN_COUNTS.items():
            for tokens in (limit, limit + 1):
                padded = ' '.join([text] + ['w{}'.format(i) for i in range(tokens - count)])
                with self.subTest(text=text, tokens=tokens):
                    boosts = typo_boosts(padded, 'names_ids.name.edge')
                    if tokens <= limit:
                        self.assertNotEqual(boosts, [])
                    else:
                        self.assertEqual(boosts, [])

    def test_word_typo_tiers_count_a_word_with_format_characters_as_one_token(self):
        limit = self.word_typo_token_limit()
        words = ['Fed\u00ader\u00adal', 'Of\u00adfice', 'Ad\u00admin\u00adis\u00adtra\u00adtion']
        words += ['w{}'.format(i) for i in range(limit - len(words))]
        plain = ' '.join(words).replace('\u00ad', '')
        self.assertNotEqual(typo_boosts(plain, 'names_ids.name.edge'), [])
        self.assertEqual(typo_boosts(' '.join(words), 'names_ids.name.edge'), typo_boosts(plain, 'names_ids.name.edge'))

    def test_index_and_query_fold_alike(self):
        compact = self.analysis['analyzer']['typeahead_compact']
        folding = [n for n in compact['filter']
                   if self.analysis['filter'].get(n, {}).get('type') not in ('length', 'truncate')]
        edge_only = {'typeahead_hangul_keys', 'typeahead_non_alnum_to_space'}
        compact_char_filters = [n for n in compact['char_filter'] if n != 'typeahead_strip_non_alnum']
        for analyzer in {self.index_analyzer, self.word_analyzer, self.ordered_tier_analyzer()}:
            chain = self.analysis['analyzer'][analyzer]
            self.assertEqual([n for n in chain['char_filter'] if n not in edge_only], compact_char_filters, analyzer)
            self.assertEqual(chain['filter'][:len(folding)], folding, analyzer)

    def test_drop_marks_deletes_every_hebrew_combining_mark_and_keeps_every_other_hebrew_character(self):
        drop_marks = re.compile(self.analysis['char_filter']['typeahead_drop_marks']['pattern'])
        hebrew_blocks = [*range(0x0590, 0x0600), *range(0xFB1D, 0xFB50)]
        mismatches = {}
        for char in map(chr, hebrew_blocks):
            category = unicodedata.category(char)
            if category != 'Cn' and (drop_marks.sub('', char) == '') != (category == 'Mn'):
                mismatches['U+{:04X}'.format(ord(char))] = category
        self.assertEqual(len(mismatches), 0, sorted(mismatches.items()))

    def test_index_and_query_join_words_on_the_same_characters(self):
        char_filters = self.analysis['char_filter']
        to_apostrophe = {source for name in char_filters for source, target in self.mapping_rules(name).items()
                         if target == "'"}
        self.assertEqual(to_apostrophe | {"'"}, typeahead._JOINERS)
        [drop_format] = [name for name, f in char_filters.items()
                         if f.get('type') == 'pattern_replace' and '\\p{Cf}' in f['pattern'] and f['replacement'] == '']
        for analyzer in {self.index_analyzer, self.word_analyzer, self.ordered_tier_analyzer(),
                         self.word_typo_analyzer(), self.exact['analyzer']}:
            chain = self.analysis['analyzer'][analyzer]['char_filter']
            [non_alnum] = [n for n in chain if char_filters[n].get('pattern', '').startswith('[^')]
            with self.subTest(analyzer=analyzer):
                self.assertLess(chain.index(drop_format), chain.index(non_alnum))

    def test_whole_name_tiers_allow_at_most_one_edit_on_any_term_the_field_emits(self):
        # Two edits on a long non-Latin term pass Lucene's 10,000-state automaton limit, and the request fails.
        [cut] = self.filters_of_type(self.exact.get('search_analyzer', self.exact['analyzer']), 'truncate')
        for text in ['Harv', 'univ of mich', '東京大', LONGEST_NAME]:
            for _, f in typeahead.tiers(text):
                for _, body in clauses_on(f.to_dict(), 'names_ids.name.exact'):
                    if isinstance(body, dict) and 'fuzziness' in body:
                        with self.subTest(text=text[:20]):
                            self.assertLessEqual(most_edits(body['fuzziness'], cut['length']), 1,
                                                 body['fuzziness'])

    def test_exact_names_fold_in_the_engine_and_drop_an_empty_term(self):
        self.assertEqual(self.exact.get('analyzer'), 'typeahead_compact')
        guard = self.analysis['analyzer']['typeahead_compact']['filter'][-1]
        self.assertEqual(self.analysis['filter'].get(guard), {'type': 'length', 'min': 1})

    def test_prefix_tier_analyzers_cut_the_term_to_at_most_1000_bytes(self):
        fields = sorted({field for _, f in typeahead.tiers('Harv')
                         for _, kind, field, _ in walk(f.to_dict()) if kind == 'match_bool_prefix'})
        self.assertNotEqual(fields, [])
        for field in fields:
            mapping = self.mapped[field]
            analyzer = mapping.get('search_analyzer', mapping.get('analyzer'))
            with self.subTest(field=field, analyzer=analyzer):
                names = self.analysis['analyzer'][analyzer]['filter']
                types = [self.analysis['filter'].get(n, {}).get('type', n) for n in names]
                self.assertIn('truncate', types)
                cut = types.index('truncate')
                length = self.analysis['filter'][names[cut]]['length']
                self.assertLessEqual(length * MAX_UTF8_BYTES_PER_UTF16_UNIT, LUCENE_MAX_PREFIX_BYTES)
                self.assertEqual([t for t in types[cut + 1:] if t != 'length'], [])

    def test_non_word_classes_never_start_inside_a_surrogate_pair(self):
        negated = {name: f['pattern'] for name, f in self.analysis['char_filter'].items()
                   if f.get('type') == 'pattern_replace' and f['pattern'].startswith('[^')}
        self.assertEqual(sorted(negated), ['typeahead_non_alnum_to_space', 'typeahead_strip_non_alnum'])
        for name, pattern in negated.items():
            with self.subTest(char_filter=name):
                negated_class = pattern[2:pattern.index(']')]
                self.assertIn('\\p{Cs}', negated_class, name)
