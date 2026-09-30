import os
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
