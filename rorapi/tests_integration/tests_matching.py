import os
import re
import requests

from django.test import SimpleTestCase

BASE_URL = '{}/organizations'.format(
    os.environ.get('ROR_BASE_URL', 'http://localhost'))


class APIMatchingTestCase(SimpleTestCase):
    def test_query_organizations(self):
        output = requests.get(BASE_URL, {
            'affiliation': 'university of warsaw'
        }).json()

        self.assertTrue(output['number_of_results'] > 1)

        for k in ['number_of_results', 'items']:
            self.assertTrue(k in output)

        prev = 1
        for i in output['items']:
            for k in [
                    'substring', 'score', 'matching_type', 'chosen',
                    'organization'
            ]:
                self.assertTrue(k in i)

            for k in ['id', 'name']:
                self.assertTrue(k in i.get('organization'))
                self.assertIsNotNone(
                    re.match(r'https:\/\/ror\.org\/0\w{6}\d{2}',
                             i.get('organization').get('id')))

            self.assertEqual(i.get('substring'), 'university of warsaw')
            self.assertTrue(i.get('score') > 0)
            self.assertTrue(i.get('score') <= 1)
            self.assertTrue(i.get('score') <= prev)
            prev = i.get('score')
            self.assertTrue(
                i.get('matching_type') in
                ['PHRASE', 'ACRONYM', 'FUZZY', 'HEURISTICS', 'COMMON TERMS', 'EXACT'])
