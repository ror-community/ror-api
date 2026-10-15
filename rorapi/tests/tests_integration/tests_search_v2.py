import os
import random
import re
import unicodedata
import requests

from django.test import SimpleTestCase

BASE_URL = '{}/v2/organizations'.format(
    os.environ.get('ROR_BASE_URL', 'http://localhost'))


class QueryTestCase(SimpleTestCase):
    def test_exact(self):
        items = requests.get(BASE_URL, {
            'query': 'Centro Universitário do Maranhão'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(BASE_URL, {
            'query': 'Julius-Maximilians-Universität Würzburg'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_lowercase(self):
        items = requests.get(BASE_URL, {
            'query': 'centro universitário do maranhão'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(BASE_URL, {
            'query': 'julius-maximilians-universität würzburg'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_accents_stripped(self):
        items = requests.get(BASE_URL, {
            'query': 'centro universitario do maranhao'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(BASE_URL, {
            'query': 'julius-maximilians-universitat wurzburg'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_extra_word(self):
        items = requests.get(BASE_URL, {
            'query': 'Centro Universitário do Maranhão School'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL, {
                'query': 'Julius-Maximilians-Universität Würzburg School'
            }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/00fbnyb24')


class QueryFuzzyTestCase(SimpleTestCase):
    def test_exact(self):
        items = requests.get(BASE_URL, {
            'query': 'Centro~ Universitário~ do~ Maranhão~'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL, {
                'query': 'Julius~ Maximilians~ Universität~ Würzburg~'
            }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_lowercase(self):
        items = requests.get(BASE_URL, {
            'query': 'centro~ universitário~ do~ maranhão~'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL, {
                'query': 'julius~ maximilians~ universität~ würzburg~'
            }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_accents_stripped(self):
        items = requests.get(BASE_URL, {
            'query': 'centro~ universitario~ do~ maranhao~'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL, {
                'query': 'julius~ maximilians~ universitat~ wurzburg~'
            }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_typos(self):
        items = requests.get(BASE_URL, {
            'query': 'centre~ universitario~ do~ marahao~'
        }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL, {
                'query': 'julius~ maximilian~ universitat~ wuerzburg~'
            }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/03pvr2g57')

    def test_extra_word(self):
        items = requests.get(
            BASE_URL, {
                'query': 'Centro~ Universitário~ do~ Maranhão~ School~'
            }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL, {
                'query': 'Julius~ Maximilians~ Universität~ Würzburg~ School~'
            }).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/00fbnyb24')


class QueryFieldReachTestCase(SimpleTestCase):
    """query and query.advanced reach no typeahead field.

    query.advanced searches root documents, so _exists_ and the default `*` expansion on it match
    no typeahead field inside names_ids. Field syntax on query does reach the typeahead subfields,
    a gap ARCHITECTURE.md documents, so the two query subtests fail. Requires an index created from
    the current index_template_es7.json.
    """

    def test_typeahead_fields_match_nothing_by_name(self):
        for params in ({'query': 'names_ids.types:acronym'},
                       {'query': 'names_ids.name.edge:harvard'},
                       {'query.advanced': '_exists_:names_ids.prior'}):
            with self.subTest(params=params):
                response = requests.get(BASE_URL, params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['number_of_results'], 0)

    def test_long_hangul_fuzzy_term_answers_json(self):
        response = requests.get(BASE_URL, {'query.advanced': '서울대학교병원국립암센터한국과학기술원연세대~'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Type'].split(';')[0], 'application/json')
        self.assertEqual(response.json()['number_of_results'], 0)


class CaseAndAccentInsensitiveTestCase(SimpleTestCase):
    """Case- and diacritic-insensitive matching (ror-roadmap#175, #398).

    Requires an index created from the current index_template_es7.json.
    """

    def search(self, **params):
        return requests.get(BASE_URL, params).json()

    def assert_same_results(self, variants, param='query.advanced'):
        results = [self.search(**{param: v}) for v in variants]
        baseline = results[0]
        self.assertTrue(baseline['number_of_results'] > 0, variants[0])
        baseline_ids = {i['id'] for i in baseline['items']}
        for variant, result in zip(variants[1:], results[1:]):
            self.assertEqual(result['number_of_results'],
                             baseline['number_of_results'], variant)
            self.assertEqual({i['id'] for i in result['items']},
                             baseline_ids, variant)

    def test_keyword_field_case(self):
        self.assert_same_results([
            'locations.geonames_details.name:Denver',
            'locations.geonames_details.name:denver',
            'locations.geonames_details.name:DENVER',
        ])

    def test_relationship_type_case(self):
        self.assert_same_results([
            'relationships.type:child',
            'relationships.type:Child',
        ])

    def test_bare_term_case(self):
        self.assert_same_results(['Stellenbosch', 'stellenbosch'])

    def test_keyword_field_diacritics(self):
        self.assert_same_results([
            'locations.geonames_details.name:Huế',
            'locations.geonames_details.name:Hue',
            'locations.geonames_details.name:hue',
        ])
        self.assert_same_results([
            'locations.geonames_details.name:Montréal',
            'locations.geonames_details.name:Montreal',
        ])

    def test_nfd_and_nfc_input(self):
        nfc = 'locations.geonames_details.name:Hu\u1ebf'
        nfd = 'locations.geonames_details.name:Hu\u0065\u0302\u0301'
        self.assertNotEqual(nfc, nfd)
        self.assert_same_results([nfc, nfd])

    def test_text_field_diacritics(self):
        self.assert_same_results([
            'names.value:"Université de Montréal"',
            'names.value:"Universite de Montreal"',
            'names.value:"universite de montreal"',
        ])

    def test_filter_case(self):
        self.assert_same_results(['Denver'], param='query')
        upper = requests.get(BASE_URL, {'filter': 'types:Education'}).json()
        lower = requests.get(BASE_URL, {'filter': 'types:education'}).json()
        self.assertTrue(upper['number_of_results'] > 0)
        self.assertEqual(upper['number_of_results'],
                         lower['number_of_results'])

    def test_aggregation_keys_keep_original_casing(self):
        # Bucket titles are derived from the raw (un-normalized) keys, e.g. the
        # country name is looked up from the upper-case ISO code.
        meta = self.search(**{'query.advanced': 'locations.geonames_details.name:denver'})['meta']
        countries = {b['id']: b['title'] for b in meta['countries']}
        self.assertEqual(countries.get('us'), 'United States')
        continents = {b['id']: b['title'] for b in meta['continents']}
        self.assertEqual(continents.get('na'), 'North America')


class TypeaheadTestCase(SimpleTestCase):
    """Searches query.typeahead and names each record by the last segment of its ROR ID."""

    def search(self, text):
        response = requests.get(BASE_URL, {'query.typeahead': text, 'page_size': 20})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertNotIn('errors', result)
        return result

    def ids(self, text):
        return [i['id'].rsplit('/', 1)[-1] for i in self.search(text)['items']]

    def position(self, ids, ror_id):
        self.assertIn(ror_id, ids)
        return ids.index(ror_id)

    def matched_name(self, text, ror_id):
        names = {i['id'].rsplit('/', 1)[-1]: i['matched_name'] for i in self.search(text)['items']}
        self.assertIn(ror_id, names)
        return names[ror_id]

    def child_count(self, ror_id):
        # Results sort on the prior, log1p of this count, before the matched name's rank.
        record = requests.get('{}/{}'.format(BASE_URL, ror_id)).json()
        return sum(1 for r in record['relationships'] if r['type'] == 'child')

    def assert_first(self, cases):
        for text, ror_id in cases:
            with self.subTest(text=text):
                self.assertEqual(self.ids(text)[:1], [ror_id])

    def assert_same_ranked_results(self, groups):
        for label, inputs in groups.items():
            with self.subTest(group=label):
                results = [self.search(text) for text in inputs]
                baseline = results[0]
                self.assertTrue(baseline['number_of_results'] > 0, inputs[0])
                baseline_ids = [i['id'] for i in baseline['items']]
                for text, result in zip(inputs[1:], results[1:]):
                    self.assertEqual(result['number_of_results'],
                                     baseline['number_of_results'], text)
                    self.assertEqual([i['id'] for i in result['items']],
                                     baseline_ids, text)

    def assert_same_count(self, pairs):
        for text, other in pairs:
            with self.subTest(text=text):
                self.assertEqual(self.search(text)['number_of_results'], self.search(other)['number_of_results'])


class TypeaheadFoldingTestCase(TypeaheadTestCase):
    """query.typeahead folds script variants alike at index and query time.

    Requires an index created from the current index_template_es7.json.
    """

    GROUPS = {
        'greek_accents': [
            'Πανεπιστήμιο Αθηνών',
            'Πανεπιστημιο Αθηνων',
        ],
        'greek_capitals_and_final_sigma': [
            'Ελληνικός Ερυθρός Σταυρός',
            'ΕΛΛΗΝΙΚΌΣ ΕΡΥΘΡΌΣ ΣΤΑΥΡΌΣ',
        ],
        'arabic_hamza_alef': [
            'جامعة الإسكندرية',
            'جامعة الاسكندرية',
        ],
        'arabic_teh_marbuta': [
            'جامعة الإسكندرية',
            'جامعه الإسكندريه',
        ],
        'arabic_alef_maksura': [
            'مستشفى السلطان قابوس',
            'مستشفي السلطان قابوس',
        ],
        'persian_yeh': [
            'دانشگاه شیراز',
            'دانشگاه شيراز',
        ],
        'persian_keheh': [
            'دانشگاه کردستان',
            'دانشگاه كردستان',
        ],
        'arabic_tatweel': [
            'جامع\u0640\u0640\u0640ة جدة',
            'جامعة جدة',
        ],
        'modifier_apostrophe': [
            'Kapi\u02bbolani Technical',
            'Kapiolani Technical',
        ],
        'caron_g_folds_to_lowercase': [
            '\u01e6\u0101ma\u02bfat al-Ba\u1e25rayn',
            'G\u0101ma\u02bfat al-Ba\u1e25rayn',
        ],
        'cyrillic_yo': [
            'Корол\u0451ва',
            'Корол\u0435ва',
        ],
        'combining_stress_mark': [
            'Мі\u0301нскі Рады\u0451тэхні\u0301чны',
            'Мінскі Рады\u0451тэхнічны',
        ],
        'combining_dot_above': [
            'Antalya Belek \u00dcni\u0307versi\u0307tesi\u0307',
            'Antalya Belek \u00dcniversitesi',
        ],
        'hebrew_points': [
            '\u05de\u05b4\u05e9\u05b0\u05c2\u05e8\u05b7\u05d3 \u05d4\u05b7\u05d1\u05b4\u05bc\u05d8\u05b8\u05bc\u05d7\u05d5\u05b9\u05df',
            'משרד הבטחון',
        ],
    }

    def test_variants_return_the_same_ranked_results(self):
        self.assert_same_ranked_results(self.GROUPS)


class TypeaheadIntrawordTestCase(TypeaheadTestCase):
    """query.typeahead joins a word around an apostrophe or an invisible format character.

    The index holds the joined word and its parts, and the query sends the joined word, so a name
    is found whether its apostrophe is typed, left out, or written as a curly quote or an okina,
    and a name stored with soft hyphens or zero width joiners is found by its plain spelling. The
    parts keep their own positions, so a prefix typed with a space for the apostrophe finds the name
    near the top. Requires an index created from the current index_template_es7.json.
    """

    GROUPS = {
        'apostrophe_inside_a_word': ['Hawaii', "Hawai'i", 'Hawai\u2019i', 'Hawai\u02bbi'],
        'apostrophe_before_another_word': ['Hawaii Hilo', "Hawai'i Hilo", 'Hawai\u02bbi Hilo'],
        'okina_typed_as_an_apostrophe': ['temir yo\u02bbl', "temir yo'l", 'temir yo\u2019l'],
    }
    FIRST = [
        ("temir yo'l", '00jxr5c40'),
        ("Hawai'i Hilo", '02mp2av58'),
    ]
    ON_THE_FIRST_PAGE = [
        ('federal office admin', '04n9aye53'),
        ('පාලි විශ්වවිද්යාලය', '01wx5mw98'),
        ('वनस्पति स्वास्थ्य प्रबंधन', '000t17x96'),
    ]
    # Deleting the apostrophe at index time, putting the parts at one position, or counting a possessive
    # name one word shorter changes these pages.
    KEPT_WITHIN = [
        ('Aquila', '01j9p1r26', 3),
        ('Cent Hospitalier Universitaire d A', '0250ngj72', 1),
        ('Arizona', '03efmqc40', 1),
    ]

    def test_apostrophe_spellings_return_the_same_ranked_results(self):
        self.assert_same_ranked_results(self.GROUPS)

    def test_ranks_the_name_first_when_its_apostrophe_is_typed(self):
        self.assert_first(self.FIRST)

    def test_finds_a_name_stored_with_format_characters_by_its_plain_spelling(self):
        for text, ror_id in self.ON_THE_FIRST_PAGE:
            with self.subTest(text=text):
                self.assertIn(ror_id, self.ids(text))

    def test_an_apostrophe_neither_lifts_nor_buries_a_name(self):
        for text, ror_id, within in self.KEPT_WITHIN:
            with self.subTest(text=text):
                self.assertIn(ror_id, self.ids(text)[:within])


class TypeaheadHangulImeTestCase(TypeaheadTestCase):
    """query.typeahead finds a Hangul name from every string a Korean IME shows while composing it.

    Requires an index created from the current index_template_es7.json.
    """

    SNU = '04h9pn542'
    # What 2-set (Microsoft, libhangul) and 3-set IMEs show while typing 서울대학교; none is a prefix of it.
    COMPOSING_STATES = ['ㅅ', '성', '서ㅇ', '서우', '서울ㄷ', '서울댛', '서울대ㅎ', '서울대하', '서울대학ㄱ', '서울대핚']

    def test_every_composing_state_finds_the_name(self):
        for state in self.COMPOSING_STATES:
            with self.subTest(state=state):
                self.assertIn(self.SNU, self.ids(state))

    def test_a_literal_prefix_ranks_above_a_composing_one(self):
        self.assertIn(self.SNU, self.ids('성'))
        starts_with_shown = [i['matched_name']['value'].startswith('성') for i in self.search('성')['items']]
        self.assertIn(True, starts_with_shown)
        self.assertEqual(starts_with_shown, sorted(starts_with_shown, reverse=True))


def folded_words(name):
    decomposed = unicodedata.normalize('NFKD', name)
    return re.findall(r'\w+', ''.join(c for c in decomposed if not unicodedata.combining(c)).casefold())


class TypeaheadTrailingWordTestCase(TypeaheadTestCase):
    """query.typeahead keeps a last word that is still being typed, even one the word tiers drop.

    A legal form followed by a period is a finished word, and the word tiers drop it.
    """

    def test_unfinished_connector_ranks_names_that_continue_it(self):
        def continues_planck(name):
            words = folded_words(name)
            return 'planck' in words and any(w.startswith('in') for w in words[words.index('planck') + 1:])

        names = [i['matched_name']['value'] for i in self.search('Planck In')['items'][:5]]
        self.assertEqual([n for n in names if not continues_planck(n)], [])

    def test_unfinished_last_letter_selects_names_that_have_it(self):
        results = {letter: self.search('Univ of ' + letter)['items'] for letter in ('A', 'E')}
        self.assertNotEqual([i['id'] for i in results['A']], [i['id'] for i in results['E']])
        for letter, items in results.items():
            names = [i['matched_name']['value'] for i in items]
            self.assertEqual([n for n in names if not any(w.startswith(letter.lower()) for w in folded_words(n))],
                             [], letter)

    def test_drops_a_legal_form_followed_by_a_period(self):
        university, research_corporation = '02xawj266', '01gddze50'
        self.assertEqual(self.child_count(university), self.child_count(research_corporation))
        self.assertEqual(self.ids('Central Michigan University Co')[:1], [research_corporation])
        self.assertEqual(self.ids('Central Michigan University Co.')[:1], [university])


class TypeaheadUnsearchableInputTestCase(TypeaheadTestCase):
    """query.typeahead returns an empty list for input the engine cannot search, not every record and
    not an error.

    The inputs pass validation but fold away entirely in Elasticsearch: letters newer than the
    engine's Unicode tables, a lone modifier apostrophe, a tatweel, and symbols that analyze to no
    token. Requires an index created from the current index_template_es7.json.
    """

    INPUTS = ['\u9ffd', '\u0870', '\ua7c0', '\u02bb', '\u0640', '\u2476', '\u00bd']

    def test_returns_an_empty_list(self):
        for text in self.INPUTS:
            with self.subTest(text='U+{:04X}'.format(ord(text))):
                result = self.search(text)
                self.assertEqual(result['number_of_results'], 0)
                self.assertEqual(result['items'], [])


class TypeaheadLongInputTestCase(TypeaheadTestCase):
    """query.typeahead answers input that folds past 1,000 UTF-8 bytes with a result list, not an
    error.

    Lucene refuses a prefix term above 1,000 bytes, and asciifolding turns each of U+247D..U+2487,
    3 bytes, into (10) through (20), 4 bytes, so 251 of them fold past the cap. A cut that splits
    the surrogate pair of a letter above U+FFFF must not error either. Requires an index created
    from the current index_template_es7.json.
    """

    INPUTS = ['a' * 997 + '\u247d', '\u247d' * 251, '\u2487' * 400, '\U00020bb7' * 300]

    def test_answers_with_a_result_list(self):
        for text in self.INPUTS:
            with self.subTest(text=text[:4], length=len(text)):
                self.assertIsInstance(self.search(text)['items'], list)


class TypeaheadRepeatedWordTestCase(TypeaheadTestCase):
    """query.typeahead matches as many records for an input that repeats a word as for the same
    input without the second copy.

    The word tiers count distinct words toward minimum_should_match, so a second "Health" cannot lift
    a name that shares only "Health" and one other word into a partial tier. Each pair repeats a
    required word, because connectors and legal forms do not count at all. Requires an index created
    from the current index_template_es7.json.
    """

    PAIRS = [
        ('National Institute on Minority Health and Health Disparities',
         'National Institute on Minority Health and Disparities'),
        ('Sichuan Academy of Medical Science and Sichuan Provincial People\u2019s Hospital',
         'Sichuan Academy of Medical Science and Provincial People\u2019s Hospital'),
        ("College of Saint Benedict and Saint John's University",
         "College of Saint Benedict and John's University"),
    ]

    def test_matches_as_many_records_as_without_the_repeat(self):
        self.assert_same_count(self.PAIRS)


class TypeaheadOptionalWordTestCase(TypeaheadTestCase):
    """query.typeahead matches as many records for an input with connectors or legal forms as for the
    same input without them.

    The word tiers count only the required words toward minimum_should_match. A connector or legal
    form would otherwise count as a matched word wherever it is an edge prefix of an unrelated word
    ("de" of Département, "co" of Commerce), admitting thousands of names that share one real word
    and pushing the name the user wants off the first page.
    """

    PAIRS = [
        ('Universidad de la Republica', 'Universidad Republica'),
        ('Spintronique et Technologie des Co', 'Spintronique Technologie Co'),
        ('Chungnam National University College of Medicine', 'Chungnam National University College Medicine'),
    ]
    ON_THE_FIRST_PAGE = ('Chungnam National University College of Medicine', '0227as991')

    def test_matches_as_many_records_as_without_the_optional_words(self):
        self.assert_same_count(self.PAIRS)

    def test_keeps_the_university_on_the_first_page_for_a_long_input_with_a_connector(self):
        text, ror_id = self.ON_THE_FIRST_PAGE
        self.assertIn(ror_id, self.ids(text))


class TypeaheadDoubledCharacterTestCase(TypeaheadTestCase):
    """query.typeahead matches a character typed twice only where a name has it twice.

    The ordered tiers need each copy of a character, in order, so a name that has the character once
    does not rank among the names that have it twice. Those tiers allow gaps, so a name that holds the
    typed characters apart (中国医学科学院北京协和医学院 for 中医医院) may still rank above the
    contiguous name, which then stays on the first page. Requires an index created from the current
    index_template_es7.json.
    """

    FIRST = [
        ('职工工学', '02m8xrg19'),
        ('法人人工', '059czkb40'),
        ('科学学会', '04het4147'),
        ('物学学会', '03kgwfd55'),
    ]
    ON_THE_FIRST_PAGE = ('中医医院', '03hy9zy10')

    def test_ranks_the_name_with_the_doubled_character_first(self):
        self.assert_first(self.FIRST)

    def test_keeps_the_name_with_the_doubled_character_on_the_first_page(self):
        text, ror_id = self.ON_THE_FIRST_PAGE
        self.assertIn(ror_id, self.ids(text))


class TypeaheadMixedScriptRankTestCase(TypeaheadTestCase):
    """query.typeahead ranks a name that joins Latin letters or digits to Han or Kana by its tokens.

    name_rank counts tokens, not words, so 三菱FBRシステムズ株式会社 (8 tokens, one word) ranks
    below 三菱アルミニウム (3 tokens) at the same tier. In each pair below the two records share a
    tier and a prior, and the second has a mixed-script name that would outrank the first record's
    name if it counted as one word. An ID off the first page ranks below every ID on it. Requires
    an index built by the current code, because the rank is stored at index time.
    """

    ABOVE = [
        ('三菱', '03s83n021', '05nfrar05'),
        ('JFE', '0289e7422', '049nfwr75'),
        ('中国人民解放军', '05bhd7f62', '02zztqs66'),
    ]

    def test_ranks_the_name_with_fewer_tokens_first(self):
        for text, above, below in self.ABOVE:
            with self.subTest(text=text):
                self.assertEqual(self.child_count(above), self.child_count(below))
                ids = self.ids(text)
                self.assertNotIn(below, ids[:self.position(ids, above)])


class TypeaheadAstralLetterTestCase(TypeaheadTestCase):
    """query.typeahead counts a letter or digit above U+FFFF like any other letter or digit.

    Typed after a name, it narrows the results the way a letter that no name contains does, instead
    of vanishing. Requires an index created from the current index_template_es7.json.
    """

    BASES = ['Kaohsiung', '\u4e2d\u79d1\u9662']
    LETTERS_AND_DIGITS = ['\U00020bb7', '\U00010400', '\U0001e900', '\U0001d7ce']
    LETTER_IN_NO_NAME = '\ua500'

    def test_narrows_the_results_like_a_letter_no_name_contains(self):
        for base in self.BASES:
            self.assertTrue(self.search(base)['number_of_results'] > 0, base)
            control = self.search(base + ' ' + self.LETTER_IN_NO_NAME)
            control_ids = [i['id'] for i in control['items']]
            for char in self.LETTERS_AND_DIGITS:
                with self.subTest(base=base, char='U+{:04X}'.format(ord(char))):
                    result = self.search(base + ' ' + char)
                    self.assertEqual(result['number_of_results'], control['number_of_results'])
                    self.assertEqual([i['id'] for i in result['items']], control_ids)


class TypeaheadTypoTestCase(TypeaheadTestCase):
    """query.typeahead forgives a typo in any script and still ranks an exact name above its
    one-edit neighbors.

    A whole name gets at most one edit, because two edits on a long non-Latin name exceed Lucene's
    automaton limit and fail the request. Input under three letters gets no edits, so a two-letter
    keystroke matches only names that start with it. A dropped letter in a short word still finds
    the name, because the word typo tiers keep every one-edit term. A name typed only as an acronym
    gets no edit at the whole-name tier, so a typo in a short word does not rank every acronym one
    edit away above the word. Requires an index created from the current index_template_es7.json.
    """

    ONE_TYPO = [
        ('Gothnburg University', '01tm6cn81'),
        ('Selçuk Universitty', '045hgzm75'),
        ('لجاعمة الريان', '01ktn5v16'),
        ('Երկրաբանական գիտությունյերի', '03r6rhw30'),
        ('ГипроНИвавиапром', '02b1w8773'),
        ('Νοσοκομεο Κυπαρισσίας', '01ycxmm33'),
        ('长春科市技局', '05kzgnp84'),
        ('한국독회일사학회', '02vtcpw89'),
        ('הספרייה הראומית', '03be63z97'),
        ('బెంగుళూుర విశ్వవిద్యాలయం', '050j2vm64'),
        ('ヤマダコレポレーション', '02trnf558'),
        ('መቱ ዩቨርሲቲ', '01gcmye25'),
        ('โรงพยาบาลศิรริาช', '0331zs648'),
    ]
    TWO_ERRORS_IN_ONE_WORD = [
        ('Gotnburg University', '01tm6cn81'),
        ('ATILIM Univeersitsy', '04pd3v454'),
    ]
    DROPPED_LETTER_IN_A_SHORT_WORD = [
        ('Ohio Sate', '00rs6vg23'),
        ('Utah Sate', '00h6set76'),
        ('Kansas Sate', '05p1j8758'),
        ('Boston nive', '05qwgg493'),
    ]
    EXACT_AND_NEIGHBOR = [
        ('Taylor University', '005aghs32', '005781934'),
        ('DePaul University', '04xtx5t16', '02mks6v46'),
        ('Furman University', '04ytb9n23', '05cmvgr54'),
    ]
    TYPO_IN_A_SHORT_WORD = [
        ('Duek', '00py81415', '030xw6n96'),
        ('Ghet', '00cv9y106', '02fvyy542'),
        ('Iwoa', '036jqmy94', '027xkck76'),
        ('Yael', '03v76x132', '01sng4k83'),
    ]
    LONG_NAME_WITH_A_TYPO = (
        'საქართველოს საპატრიარქოს წმიდა ანდრია პირველწოდებულის სახელობის რქართული უნივერსიტეტი', '003ag3w45')
    SHORT_INPUTS = ['qx', 'xq', 'zx', 'vq']

    def test_ranks_the_name_first_despite_one_typo_in_any_script(self):
        self.assert_first(self.ONE_TYPO)

    def test_ranks_the_name_first_despite_two_errors_in_one_word(self):
        self.assert_first(self.TWO_ERRORS_IN_ONE_WORD)

    def test_ranks_the_name_first_despite_a_dropped_letter_in_a_short_word(self):
        self.assert_first(self.DROPPED_LETTER_IN_A_SHORT_WORD)

    def test_an_exact_name_outranks_its_one_edit_neighbor(self):
        for text, exact, neighbor in self.EXACT_AND_NEIGHBOR:
            with self.subTest(text=text):
                ids = self.ids(text)
                self.assertEqual(ids[:1], [exact])
                self.assertIn(neighbor, ids[1:])

    def test_ranks_a_short_word_with_a_typo_above_acronyms_one_edit_away(self):
        for text, intended, acronym in self.TYPO_IN_A_SHORT_WORD:
            with self.subTest(text=text):
                ids = self.ids(text)
                self.assertNotIn(acronym, ids[:self.position(ids, intended)])

    def test_a_long_multibyte_name_with_a_typo_answers_with_its_record_first(self):
        text, ror_id = self.LONG_NAME_WITH_A_TYPO
        self.assertEqual(self.ids(text)[:1], [ror_id])

    def test_input_under_three_letters_gets_no_typo_match(self):
        for text in self.SHORT_INPUTS:
            with self.subTest(text=text):
                self.assertEqual(self.search(text)['number_of_results'], 0)


class TypeaheadLongTypoTestCase(TypeaheadTestCase):
    """query.typeahead forgives a typo in a long name whether or not the word typo tiers run.

    The word typo tiers run only when the required words have at most 8 tokens, counted after Han
    and Hiragana pairs, and their analyzer stops at 8 tokens, because each fuzzy token walks the
    edge-gram term dictionary. Two typos in a name of 8 required words still rank its record first.
    One typo in a name of 10 still does, at the all-but-one tier. A typo in a Katakana word after
    eight Han characters still ranks its name first, at a word typo tier. The 64 words universitaa
    to universithh joined by a Thai letter count as one token toward the 8, because the count does
    not split Thai from Latin, while the analyzer splits them into dozens and must stop at 8. They
    must answer with a result list. Requires an index created from the current
    index_template_es7.json.
    """

    TWO_TYPOS_IN_EIGHT_WORDS = [
        ('Institute of Higherr Eudcation of the National Academy of Educational Sciences of Ukraine',
         '02rdthx75'),
        ('Pohdalańska Państwowa Wyższa Szkoła Zawodowa w Nowym Tarrgu', '00m94dk17'),
    ]
    ONE_TYPO_IN_TEN_WORDS = [
        ('Innovation Academy of Soutth China Sea Ecology and Environmental Engineering, SCSIO CAS',
         '034cbwf57'),
        ('U.S. National Oceanic and Atmospheric Administration Earth Systemm Research Laboratory',
         '033tt8e33'),
        ('Shandong Provincial Key Laboraotry of Eco-environmental Science for Yellow River Delta',
         '05r5axe79'),
    ]
    TYPO_AFTER_A_LONG_HAN_RUN = [('自然科学研究機構アストロバイオロジーセソ', '028z8qe34')]
    WORDS_JOINED_BY_A_THAI_LETTER = 'ก'.join('universit' + a + b for a in 'abcdefgh' for b in 'abcdefgh')

    def test_ranks_the_name_first_despite_two_typos_in_eight_required_words(self):
        self.assert_first(self.TWO_TYPOS_IN_EIGHT_WORDS)

    def test_ranks_the_name_first_despite_one_typo_in_ten_required_words(self):
        self.assert_first(self.ONE_TYPO_IN_TEN_WORDS)

    def test_ranks_the_name_first_despite_a_typo_in_a_katakana_word_after_eight_han_characters(self):
        self.assert_first(self.TYPO_AFTER_A_LONG_HAN_RUN)

    def test_words_joined_by_a_thai_letter_answer_with_a_result_list(self):
        self.assertIsInstance(self.search(self.WORDS_JOINED_BY_A_THAI_LETTER)['items'], list)


def random_letters(start, stop, count):
    return ''.join(map(chr, random.Random(0).choices(range(start, stop), k=count)))


class TypeaheadLongCjkTestCase(TypeaheadTestCase):
    """query.typeahead answers long input in a 3- or 4-byte script with a result list, not an error.

    Lucene cannot build the one-edit automaton of the whole-name typo tier for a term past about 740
    UTF-8 bytes in such a script, so the tier runs only when the input has at most 500 bytes, above
    the longest registry name. 300 random Han characters, 300 random Hangul syllables, and 300
    characters alternating Han with CJK Extension B must answer 200.
    """

    HAN = random_letters(0x4E00, 0x9FA6, 300)
    INPUTS = {
        'han': HAN,
        'hangul': random_letters(0xAC00, 0xD7A4, 300),
        'han_and_extension_b': ''.join(h + e for h, e in zip(HAN, random_letters(0x20000, 0x2A6D7, 150))),
    }

    def test_answers_with_a_result_list(self):
        for script, text in self.INPUTS.items():
            with self.subTest(script=script, utf8_bytes=len(text.encode())):
                self.assertIsInstance(self.search(text)['items'], list)


class TypeaheadNonNfcNameTestCase(TypeaheadTestCase):
    """A name the record stores in a non-NFC form finds its record when pasted back as the query.

    query.typeahead NFC-normalizes its input, and the typeahead subfields of names_ids.name
    NFC-normalize the stored spelling through the typeahead_nfc char filter.
    Requires an index built from the current template.
    """

    RECORDS = [('0015qa126', 'label', 'kn'), ('029rfe283', 'ror_display', 'fr')]

    def stored_name(self, ror_id, name_type, lang):
        record = requests.get('{}/{}'.format(BASE_URL, ror_id)).json()
        name = next(n['value'] for n in record['names']
                    if name_type in n['types'] and n.get('lang') == lang)
        self.assertFalse(unicodedata.is_normalized('NFC', name), name)
        return name

    def test_ranks_the_record_first_for_its_own_spelling(self):
        for ror_id, name_type, lang in self.RECORDS:
            name = self.stored_name(ror_id, name_type, lang)
            with self.subTest(ror_id=ror_id):
                self.assertEqual(self.ids(name)[:1], [ror_id])


class TypeaheadMatchedRankTestCase(TypeaheadTestCase):
    """Records tied on tier and prior sort on the rank of the name that matched.

    A record's tier is the best tier any of its names reaches, and matched_name is the name in that
    tier with the lowest rank value. The tie-break uses that name's rank, not a better-ranked name
    that matched only a lower tier.
    """

    def test_a_long_alias_match_sorts_below_a_tied_display_match(self):
        self.assertEqual(self.child_count('0090zs177'), self.child_count('026zzn846'))
        qmul = self.matched_name('london', '026zzn846')
        self.assertEqual(qmul['value'], 'London Hospital Medical College')
        self.assertIn('alias', qmul['types'])
        ids = self.ids('london')
        self.assertLess(self.position(ids, '0090zs177'), self.position(ids, '026zzn846'))

    def test_display_name_match_beats_an_alias_match_for_cnrs(self):
        self.assertEqual(self.child_count('05hqw3605'), self.child_count('03zv5dv41'))
        euxfel = self.matched_name('cnrs', '03zv5dv41')
        self.assertEqual(euxfel['value'], 'CNRS - EuXFEL')
        self.assertIn('alias', euxfel['types'])
        ids = self.ids('cnrs')
        self.assertLess(self.position(ids, '05hqw3605'), self.position(ids, '03zv5dv41'))

    def test_prior_sorts_before_the_matched_name_rank(self):
        self.assertGreater(self.child_count('04cw6st05'), self.child_count('04cntmc13'))
        self.assertIn('alias', self.matched_name('london', '04cw6st05')['types'])
        self.assertIn('ror_display', self.matched_name('london', '04cntmc13')['types'])
        ids = self.ids('london')
        self.assertLess(self.position(ids, '04cw6st05'), self.position(ids, '04cntmc13'))


class TypeaheadNameKindTestCase(TypeaheadTestCase):
    """A name ranks as the best of its types, and the full-name tiers take it however else it is typed.

    A name typed as an acronym and as a label, an alias or the display name is a full name: it matches
    at the exact and whole-name typo tiers of a full name and ranks as one. Within a kind fewer tokens
    rank first, and the display name beats a label with as many tokens, so a label that ties it is
    not the matched name.
    """

    def test_a_name_typed_as_an_acronym_too_ranks_first_as_a_full_name(self):
        self.assert_first([('ISEG', '04gvzsd39'), ('BASA', '05k4nys47'), ('ICEE', '0320fj966')])

    def test_display_name_is_the_matched_name_when_a_label_ties_it(self):
        for ror_id, display in [('01c27hj86', 'University of Lisbon'), ('03xjwb503', 'Université Paris-Saclay')]:
            with self.subTest(ror_id=ror_id):
                self.assertEqual(self.matched_name('univ', ror_id)['value'], display)

    def test_display_name_typed_as_an_acronym_too_is_the_matched_name(self):
        self.assertEqual(self.matched_name('EUD', '02d6dw644')['value'], 'EUDAT')

    def test_whole_name_typo_tier_reaches_a_name_typed_as_an_acronym_too(self):
        self.assertIn('04gvzsd39', self.ids('ISGE')[:5])


class TypeaheadPageRangeTestCase(SimpleTestCase):
    """query.typeahead reaches result 10,000 at page sizes that do not divide 10,000.

    The last valid page is the one that holds result 10,000, so such a page_size ends on a short
    page, and the page after it is out of range.
    """

    def page(self, page_size, page):
        params = {'query.typeahead': 'a', 'page_size': page_size, 'page': page}
        return requests.get(BASE_URL, params).json()

    def test_last_short_page_ends_on_result_10000(self):
        last = self.page(20, 500)['items'][-1]['id']
        for page_size, last_page, length in [(3, 3334, 1), (7, 1429, 4), (15, 667, 10)]:
            with self.subTest(page_size=page_size):
                result = self.page(page_size, last_page)
                self.assertNotIn('errors', result)
                self.assertEqual(len(result['items']), length)
                self.assertEqual(result['items'][-1]['id'], last)
                self.assertEqual(self.page(page_size, last_page + 1)['errors'], [
                    "page '{}' outside of range 1-{}".format(last_page + 1, last_page)])


class ExternalIdAdvancedSearchTestCase(SimpleTestCase):
    """External ID advanced search (ror-roadmap#70, #71)."""

    def test_spaced_isni_without_quotes(self):
        # query_string would otherwise split on spaces (roadmap#71)
        unquoted = requests.get(BASE_URL, {
            'query.advanced': 'external_ids.all:0000 0001 2375 2908'
        }).json()
        quoted = requests.get(BASE_URL, {
            'query.advanced': 'external_ids.all:"0000 0001 2375 2908"'
        }).json()
        self.assertTrue(quoted['number_of_results'] > 0)
        self.assertEqual(unquoted['number_of_results'],
                         quoted['number_of_results'])
        self.assertEqual(unquoted['items'][0]['id'],
                         'https://ror.org/019496w77')

    def test_fundref_via_v2_fields(self):
        items = requests.get(BASE_URL, {
            'query.advanced':
            'external_ids.type:fundref AND external_ids.all:100000908'
        }).json()
        self.assertEqual(items['number_of_results'], 1)
        self.assertEqual(items['items'][0]['id'], 'https://ror.org/02g8xhs57')

    def test_legacy_fundref_path_error_hint(self):
        items = requests.get(BASE_URL, {
            'query.advanced': 'external_ids.FundRef.all:100000908'
        }).json()
        self.assertIn('errors', items)
        self.assertTrue(any('external_ids.all' in e for e in items['errors']))
        self.assertTrue(any('schema v2' in e for e in items['errors']))
