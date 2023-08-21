from django.test import SimpleTestCase

from ..matching import load_geonames_countries, load_geonames_cities, load_countries, to_region, get_country_codes, \
    get_countries, normalize, MatchedOrganization, get_similarity, get_score, \
    MatchingNode, clean_search_string, check_do_not_match, MatchingGraph, get_output, \
    check_exact_match, MATCHING_TYPE_PHRASE, MATCHING_TYPE_COMMON, MATCHING_TYPE_FUZZY
from .utils import AttrDict


class CountriesTestCase(SimpleTestCase):
    def test_load_geonames_countries(self):
        countries = load_geonames_countries()

        self.assertTrue('AZ' in countries)
        self.assertTrue('FM' in countries)
        self.assertTrue('ZM' in countries)

    def test_load_geonames_cities(self):
        cities = load_geonames_cities()

        self.assertTrue('3031582' in cities)

    def test_load_countries(self):
        countries = load_countries()

        self.assertEqual(len(countries), 590)
        self.assertTrue(('az', 'azarbaycan respublikasi') in countries)
        self.assertTrue(('fm', 'federated states of micronesia') in countries)
        self.assertTrue(('zm', 'zambia') in countries)

    def test_to_region(self):
        self.assertEqual(to_region('PL'), 'PL')
        for c in ['GB', 'UK']:
            self.assertEqual(to_region(c), 'GB-UK')
        if c in ['CN', 'HK', 'TW']:
            self.assertEqual(to_region(c), 'CN-HK-TW')
        if c in ['PR', 'US']:
            self.assertEqual(to_region(c), 'US-PR')

    def test_get_country_codes(self):
        self.assertEqual(get_country_codes('Seoul, Korea.'), ['KR'])
        self.assertEqual(get_country_codes('Chicago, Illinois, USA'), ['US'])
        self.assertEqual(
            get_country_codes(
                'University of California, Berkeley, California'), ['US'])
        self.assertEqual(get_country_codes('Hospital Kassel, Kassel, Germany'),
                         ['DE'])
        self.assertEqual(get_country_codes('New South Wales, Australia'),
                         ['AU'])
        self.assertEqual(get_country_codes('State of Illinois'), ['US'])
        self.assertEqual(
            get_country_codes('Lehigh Valley Hospital, Allentown, PA;'),
            ['US'])
        self.assertEqual(
            get_country_codes('Boston Children\'s Hospital, Boston, MA '),
            ['US'])
        self.assertEqual(
            get_country_codes('Winthrop University Hospital, Mineola, NY'),
            ['US'])
        self.assertEqual(
            get_country_codes('Medical Dow Chemical Company, U.S.A.'), ['US'])
        self.assertEqual(get_country_codes('New York University'), ['US'])
        self.assertEqual(get_country_codes('Enschede, The Netherlands'),
                         ['NL'])
        self.assertEqual(
            get_country_codes(
                'University of Surrey, Guildford, United Kingdom'), ['UK'])
        self.assertEqual(get_country_codes('República Dominicana'), ['DO'])
        self.assertEqual(
            get_country_codes('České Budějovice ,  Czech Republic'), ['CZ'])
        self.assertEqual(get_country_codes('Washington, D.C.'), ['US'])
        self.assertEqual(
            get_country_codes('Agency for Health Care Policy and Research'),
            [])

    def test_get_country(self):
        self.assertEqual(get_countries('Seoul, Korea.'), ['KR'])
        self.assertEqual(get_countries('Chicago, Illinois, USA'), ['US-PR'])
        self.assertEqual(
            get_countries('University of California, Berkeley, California'),
            ['US-PR'])
        self.assertEqual(get_countries('Hospital Kassel, Kassel, Germany'),
                         ['DE'])
        self.assertEqual(get_countries('New South Wales, Australia'), ['AU'])
        self.assertEqual(get_countries('State of Illinois'), ['US-PR'])
        self.assertEqual(
            get_countries('Lehigh Valley Hospital, Allentown, PA;'), ['US-PR'])
        self.assertEqual(
            get_countries('Boston Children\'s Hospital, Boston, MA '),
            ['US-PR'])
        self.assertEqual(
            get_countries('Winthrop University Hospital, Mineola, NY'),
            ['US-PR'])
        self.assertEqual(get_countries('Medical Dow Chemical Company, U.S.A.'),
                         ['US-PR'])
        self.assertEqual(get_countries('New York University'), ['US-PR'])
        self.assertEqual(get_countries('Enschede, The Netherlands'), ['NL'])
        self.assertEqual(
            get_countries('University of Surrey, Guildford, United Kingdom'),
            ['GB-UK'])
        self.assertEqual(get_countries('República Dominicana'), ['DO'])
        self.assertEqual(get_countries('České Budějovice ,  Czech Republic'),
                         ['CZ'])
        self.assertEqual(get_countries('Washington, D.C.'), ['US-PR'])
        self.assertEqual(
            get_countries('Agency for Health Care Policy and Research'), [])


class NormalizeTestCase(SimpleTestCase):
    def test_normalize(self):
        self.assertEqual(normalize('university of excellence'),
                         'university of excellence')
        self.assertEqual(normalize('ünivërsity óf éxcellençe'),
                         'university of excellence')
        self.assertEqual(normalize('University  of    ExceLLence'),
                         'university of excellence')
        self.assertEqual(normalize('The University of Excellence'),
                         'university of excellence')
        self.assertEqual(normalize('University of Excellence & Brilliance'),
                         'university of excellence and brilliance')
        self.assertEqual(
            normalize('The University of Excellence & Brilliance'),
            'university of excellence and brilliance')
        self.assertEqual(normalize('U.S. University of Excellence'),
                         'united states university of excellence')
        self.assertEqual(normalize('university of tech'),
                         'university of technology')
        self.assertEqual(normalize('university of tech & Excellence'),
                         'university of technology and excellence')
        self.assertEqual(normalize('University of Tech. & Excellence'),
                         'university of technology and excellence')
        self.assertEqual(normalize('Inst. of excellence'),
                         'institute of excellence')
        self.assertEqual(normalize('Inst of Excellence'),
                         'institute of excellence')
        self.assertEqual(normalize('Inst of Excellence inst'),
                         'institute of excellence institute')
        self.assertEqual(normalize('Lab. of excellence'),
                         'laboratory of excellence')
        self.assertEqual(normalize('Lab of Excellence'),
                         'laboratory of excellence')
        self.assertEqual(normalize('lab of Excellence lab'),
                         'laboratory of excellence laboratory')
        self.assertEqual(normalize('Univ. of Excellence'),
                         'university of excellence')
        self.assertEqual(normalize('univ of Excellence'),
                         'university of excellence')
        self.assertEqual(normalize('Excellence Univ'), 'excellence university')
        self.assertEqual(normalize('U. of Excellence'),
                         'university of excellence')
        self.assertEqual(normalize('U.W.X. of Excellence'),
                         'u.w.x. of excellence')
        self.assertEqual(normalize('U. W. X. of Excellence'),
                         'u. w. x. of excellence')
        self.assertEqual(normalize('関西光科学研究所'),
                         '関西光科学研究所')
        self.assertEqual(normalize('Московский государственный университет  Russia '),
                 'московский государственный университет russia')


class MatchedOrganizationTestCase(SimpleTestCase):
    def test_init(self):
        empty = MatchedOrganization()
        self.assertTrue(empty.substring is None)
        self.assertEqual(empty.score, 0)
        self.assertEqual(empty.chosen, False)
        self.assertTrue(empty.matching_type is None)
        self.assertTrue(empty.organization is None)

        match = MatchedOrganization(substring='aff',
                                    score=60,
                                    chosen=True,
                                    matching_type='query',
                                    organization='obj')
        self.assertEqual(match.substring, 'aff')
        self.assertEqual(match.score, 60)
        self.assertEqual(match.matching_type, 'query')
        self.assertEqual(match.organization, 'obj')
        self.assertEqual(match.chosen, True)


class SimilarityTestCase(SimpleTestCase):

    V1_VERSION = 'v1'

    def test_get_similarity(self):
        self.assertEqual(
            get_similarity('University of Excellence',
                           'University of Excellence'), 1)
        self.assertEqual(
            get_similarity('univ. of excellençë', 'Univërsity of Excellence'),
            1)
        self.assertEqual(
            get_similarity('of Excellence University',
                           'University of Excellence'), 1)
        self.assertEqual(
            get_similarity('of excellençë univ', 'University of Excellence'),
            1)
        self.assertEqual(
            get_similarity('Excellence University',
                           'University of Excellence'), 0.93)
        self.assertEqual(
            get_similarity('excellençë univ', 'University of Excellence'),
            0.93)
        self.assertEqual(
            get_similarity('University of Exçellence',
                           'University of Excellence (Gallifrey)'), 1)
        self.assertEqual(
            get_similarity('University of Excellence and Brilliance',
                           'University of Excellence'), 0.76)
        self.assertEqual(
            get_similarity('University of Excellence (and Brilliance)',
                           'University of Excellence'), 1)
        self.assertEqual(
            get_similarity('University of Excellence School of Perseverance',
                           'University of Excellence'), 1)
        self.assertEqual(
            get_similarity('University of Excellence Mediocrity Hospital',
                           'University of Excellence'), 1)

    def test_get_score(self):
        empty = {
            'name': '',
            'labels': [],
            'aliases': [],
            'acronyms': [],
            'country': {
                'country_code': ''
            }
        }
        self.assertEqual(
            get_score(AttrDict(dict(empty, name='University of Excellence')),
                      'University of Excellence', None, self.V1_VERSION), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Excellence',
                         country={'country_code': 'XY'})),
                'University of Excellence', ['US-PR'], self.V1_VERSION), 0)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Excellence',
                         country={'country_code': 'PR'})),
                'University of Excellence', ['US-PR'], self.V1_VERSION), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty, labels=[{
                        'label': 'University of Excellence'
                    }])), 'University of Excellence', None, self.V1_VERSION), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         labels=[{
                             'label': 'Excellence U'
                         }, {
                             'label': 'University of Excellence'
                         }])), 'University of Excellence', None, self.V1_VERSION), 1)
        self.assertEqual(
            get_score(
                AttrDict(dict(empty, aliases=['University of Excellence'])),
                'University of Excellence', None, self.V1_VERSION), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         aliases=['Excellence U',
                                  'University of Excellence'])),
                'University of Excellence', None, self.V1_VERSION), 1)
        self.assertEqual(
            get_score(AttrDict(dict(empty, acronyms=['UEXC'])),
                      'University of Excellence', None, self.V1_VERSION), 0)
        self.assertEqual(
            get_score(AttrDict(dict(empty, acronyms=['UEXC'])), 'UEXC', None, self.V1_VERSION),
            0.9)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         acronyms=['UEXC'],
                         country={'country_code': 'PR'})), 'UEXC', ['US-PR'], self.V1_VERSION),
            1)

        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Excellence',
                         labels=[{
                             'label': 'Excellence U'
                         }, {
                             'label': 'University Excellence'
                         }],
                         aliases=['Excellence U', 'University Excellence'],
                         acronyms=['UEXC'])), 'University of Excellence',
                None, self.V1_VERSION), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University Excellence',
                         labels=[{
                             'label': 'Excellence U'
                         }, {
                             'label': 'University of Excellence'
                         }],
                         aliases=['Excellence U', 'University Excellence'],
                         acronyms=['UEXC'])), 'University of Excellence',
                None, self.V1_VERSION), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University Excellence',
                         labels=[{
                             'label': 'Excellence U'
                         }, {
                             'label': 'University Excellence'
                         }],
                         aliases=['Excellence U', 'University of Excellence'],
                         acronyms=['UEXC'])), 'University of Excellence',
                None, self.V1_VERSION), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Brilliance',
                         labels=[{
                             'label': 'University of Brilliance'
                         }],
                         aliases=['Brilliance U', 'University Brilliance'],
                         acronyms=['UEXC'])), 'UEXC', None, self.V1_VERSION), 0.9)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Brilliance',
                         labels=[{
                             'label': 'University of Brilliance'
                         }],
                         aliases=['Brilliance U', 'University Brilliance'],
                         acronyms=['UEXC'],
                         country={'country_code': 'PR'})), 'UEXC', ['US-PR'], self.V1_VERSION),
            1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Brilliance',
                         labels=[{
                             'label': 'University of Brilliance'
                         }],
                         aliases=['Brilliance U', 'University Brilliance'],
                         acronyms=['UEXC'],
                         country={'country_code': 'AV'})), 'UEXC', ['US-PR'], self.V1_VERSION),
            0)


class TestMatchingNode(SimpleTestCase):

    V1_VERSION = 'v1'

    def test_init(self):
        empty = MatchingNode('text', self.V1_VERSION)
        self.assertEqual(empty.text, 'text')
        self.assertTrue(empty.matched is None)

class TestCleanSearchString(SimpleTestCase):
    def test_init(self):
        self.assertEqual(clean_search_string('university of excellence'),
                         'university of excellence')
        self.assertEqual(clean_search_string('ünivërsity óf éxcellençe'),
                         'ünivërsity óf éxcellençe')
        self.assertEqual(clean_search_string('University  of    ExceLLence'),
                         'University of ExceLLence')
        self.assertEqual(clean_search_string('The University of Excellence'),
                         'The University of Excellence')
        self.assertEqual(clean_search_string('University of Excellence & Brilliance'),
                         'University of Excellence & Brilliance')
        self.assertEqual(clean_search_string('U.S. University of Excellence'),
                         'U S University of Excellence')
        self.assertEqual(clean_search_string('University of Tech. & Excellence'),
                         'University of Tech & Excellence')
        self.assertEqual(clean_search_string('University of Tech, Excellence'),
                         'University of Tech Excellence')
        self.assertEqual(clean_search_string('University of Tech/Excellence'),
                         'University of Tech Excellence')
        self.assertEqual(clean_search_string('University of Tech: Excellence'),
                         'University of Tech Excellence')
        self.assertEqual(clean_search_string('University of Tech; Excellence'),
                         'University of Tech Excellence')
        self.assertEqual(clean_search_string('University of Tech Excellence;'),
                         'University of Tech Excellence')

class TestCheckDoNotMatch(SimpleTestCase):
    def test_init(self):
        self.assertTrue(check_do_not_match('university hospital')),
        self.assertTrue(check_do_not_match('MX')),
        self.assertTrue(check_do_not_match('Mexico')),
        self.assertTrue(check_do_not_match('MEX')),
        self.assertTrue(check_do_not_match('Bordeaux')),
        self.assertFalse(check_do_not_match('university of excellence'))

class TestMatchingGraph(SimpleTestCase):

    V1_VERSION = 'v1'

    def test_init(self):
        graph = MatchingGraph('University of Excellence', self.V1_VERSION)
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(graph.nodes[0].text, 'University of Excellence')
        self.assertEqual(graph.nodes[1].text, 'University of Excellence')

        graph = \
            MatchingGraph('University of Excellence and Creativity Institute', self.V1_VERSION)
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(graph.nodes[0].text, 'University of Excellence and Creativity Institute')
        self.assertEqual(graph.nodes[1].text, 'University of Excellence and Creativity Institute')

        graph = \
            MatchingGraph('University of Excellence & Creativity Institute', self.V1_VERSION)
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(graph.nodes[0].text,
                         'University of Excellence & Creativity Institute')
        self.assertEqual(graph.nodes[1].text,
                         'University of Excellence & Creativity Institute')

        graph = MatchingGraph(
            'University of Excellence &amp; Creativity Institute', self.V1_VERSION)
        self.assertEqual(len(graph.nodes), 2)
        self.assertEqual(graph.nodes[0].text,
                         'University of Excellence & Creativity Institute')
        self.assertEqual(graph.nodes[1].text,
                         'University of Excellence & Creativity Institute')

        graph = MatchingGraph('University of Excellence, Creativity Institute', self.V1_VERSION)
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(graph.nodes[0].text,
                         'University of Excellence Creativity Institute')
        self.assertEqual(graph.nodes[1].text, 'University of Excellence')
        self.assertEqual(graph.nodes[2].text, 'Creativity Institute')


        graph = MatchingGraph('School of Brilliance, University of ' +
                              'Excellence and Perseverance; 21-100 ' +
                              'Gallifrey: Outerspace', self.V1_VERSION)
        self.assertEqual(len(graph.nodes), 5)
        self.assertEqual(graph.nodes[0].text, 'School of Brilliance University of Excellence and Perseverance 21 100 Gallifrey Outerspace')
        self.assertEqual(graph.nodes[1].text, 'School of Brilliance')
        self.assertEqual(graph.nodes[2].text, 'University of Excellence and Perseverance')
        self.assertEqual(graph.nodes[3].text, '21 100 Gallifrey')
        self.assertEqual(graph.nodes[4].text, 'Outerspace')

    def test_remove_low_scores(self):
        graph = MatchingGraph('University of Excellence, Creativity Institute', self.V1_VERSION)
        graph.nodes[0].matched = MatchedOrganization(substring='s0',
                                                     score=10,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[1].matched = MatchedOrganization(substring='s1',
                                                     score=100,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[2].matched = MatchedOrganization(substring='s2',
                                                     score=67,
                                                     matching_type='q',
                                                     organization='obj')
        graph.remove_low_scores(90)
        self.assertTrue(graph.nodes[0].matched is None)
        self.assertTrue(graph.nodes[1].matched is not None)
        self.assertEqual(graph.nodes[1].matched.substring, 's1')
        self.assertTrue(graph.nodes[2].matched is None)

class TestGenerateOutput(SimpleTestCase):
    def org(self, substring, score, type, id, chosen=False):
        return MatchedOrganization(substring=substring,
                                   score=score,
                                   matching_type=type,
                                   chosen=chosen,
                                   organization=AttrDict({'id': id}))

    def test_get_output(self):
        c1 = self.org('s 1', 1, MATCHING_TYPE_PHRASE, 'org1')
        c2 = self.org('s 2', 0.94, MATCHING_TYPE_FUZZY, 'org2')

        m1 = self.org('s 2', 1, MATCHING_TYPE_COMMON, 'org1')
        m2 = self.org('s 1', 1, MATCHING_TYPE_PHRASE, 'org1')
        m3 = self.org('s 1', 1, MATCHING_TYPE_FUZZY, 'org1')

        m4 = self.org('s 2', 1, MATCHING_TYPE_PHRASE, 'org2')
        m5 = self.org('s 2', 0.94, MATCHING_TYPE_FUZZY, 'org2')

        m6 = self.org('s 3', 0.5, MATCHING_TYPE_COMMON, 'org3')
        m7 = self.org('s 4', 0.66, MATCHING_TYPE_PHRASE, 'org3')
        m8 = self.org('s 5', 0.49, MATCHING_TYPE_FUZZY, 'org3')

        m9 = self.org('s 3', 0.76, MATCHING_TYPE_COMMON, 'org4')
        m10 = self.org('s 4', 0.76, MATCHING_TYPE_PHRASE, 'org4')

        m11 = self.org('s 3', 0.48, MATCHING_TYPE_FUZZY, 'org5')
        m12 = self.org('s 4', 0.06, MATCHING_TYPE_PHRASE, 'org5')
        m13 = self.org('s 55', 0.48, MATCHING_TYPE_FUZZY, 'org5')

        c1_ch = self.org('s 1', 1, MATCHING_TYPE_PHRASE, 'org1', chosen=False)

        self.assertEquals(
            get_output(
                [c1, c2],
                [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13], False),
            [c1_ch, m4, m10, m7])