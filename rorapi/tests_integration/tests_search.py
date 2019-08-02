import os
import requests

from django.test import SimpleTestCase

BASE_URL = '{}/organizations'.format(
    os.environ.get('ROR_BASE_URL', 'http://localhost'))


class QueryTestCase(SimpleTestCase):

    def test_exact(self):
        items = requests.get(
            BASE_URL, {'query': 'Centro Universitário do Maranhão'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query': 'Julius-Maximilians-Universität Würzburg'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_lowercase(self):
        items = requests.get(
            BASE_URL, {'query': 'centro universitário do maranhão'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query': 'julius-maximilians-universität würzburg'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_accents_stripped(self):
        items = requests.get(
            BASE_URL, {'query': 'centro universitario do maranhao'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query': 'julius-maximilians-universitat wurzburg'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_extra_word(self):
        items = requests.get(
            BASE_URL,
            {'query': 'Centro Universitário do Maranhão School'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query': 'Julius-Maximilians-Universität Würzburg School'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')


class QueryFuzzyTestCase(SimpleTestCase):

    def test_exact(self):
        items = requests.get(
            BASE_URL, {'query': 'Centro~ Universitário~ do~ Maranhão~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query': 'Julius~ Maximilians~ Universität~ Würzburg~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_lowercase(self):
        items = requests.get(
            BASE_URL, {'query': 'centro~ universitário~ do~ maranhão~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query': 'julius~ maximilians~ universität~ würzburg~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_accents_stripped(self):
        items = requests.get(
            BASE_URL, {'query': 'centro~ universitario~ do~ maranhao~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query': 'julius~ maximilians~ universitat~ wurzburg~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_typos(self):
        items = requests.get(
            BASE_URL, {'query': 'centre~ universitario~ do~ marahao~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query': 'julius~ maximilian~ universitat~ wuerzburg~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')

    def test_extra_word(self):
        items = requests.get(
            BASE_URL,
            {'query': 'Centro~ Universitário~ do~ Maranhão~ School~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/044g0p936')

        items = requests.get(
            BASE_URL,
            {'query':
             'Julius~ Maximilians~ Universität~ Würzburg~ School~'}).json()
        self.assertTrue(items['number_of_results'] > 0)
        self.assertEquals(items['items'][0]['id'], 'https://ror.org/00fbnyb24')
