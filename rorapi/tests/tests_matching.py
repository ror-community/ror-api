from django.test import SimpleTestCase

from ..matching import load_countries, to_region, get_country_codes, \
    get_countries, normalize, MatchedOrganization, get_similarity, get_score, \
    MatchingNode, MatchingGraph, get_output, MATCHING_TYPE_PHRASE, \
    MATCHING_TYPE_COMMON, MATCHING_TYPE_FUZZY
from .utils import AttrDict


class CountriesTestCase(SimpleTestCase):
    def test_load_countries(self):
        countries = load_countries()

        self.assertEqual(len(countries), 588)
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
        self.assertEqual(get_similarity('excellençë', 'Excellence'), 1)
        self.assertEqual(get_similarity('excellençë', 'Excellenc'), 0)
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
                      'University of Excellence', None), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Excellence',
                         country={'country_code': 'XY'})),
                'University of Excellence', ['US-PR']), 0)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Excellence',
                         country={'country_code': 'PR'})),
                'University of Excellence', ['US-PR']), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty, labels=[{
                        'label': 'University of Excellence'
                    }])), 'University of Excellence', None), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         labels=[{
                             'label': 'Excellence U'
                         }, {
                             'label': 'University of Excellence'
                         }])), 'University of Excellence', None), 1)
        self.assertEqual(
            get_score(
                AttrDict(dict(empty, aliases=['University of Excellence'])),
                'University of Excellence', None), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         aliases=['Excellence U',
                                  'University of Excellence'])),
                'University of Excellence', None), 1)
        self.assertEqual(
            get_score(AttrDict(dict(empty, acronyms=['UEXC'])),
                      'University of Excellence', None), 0)
        self.assertEqual(
            get_score(AttrDict(dict(empty, acronyms=['UEXC'])), 'UEXC', None),
            0.9)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         acronyms=['UEXC'],
                         country={'country_code': 'PR'})), 'UEXC', ['US-PR']),
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
                None), 1)
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
                None), 1)
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
                None), 1)
        self.assertEqual(
            get_score(
                AttrDict(
                    dict(empty,
                         name='University of Brilliance',
                         labels=[{
                             'label': 'University of Brilliance'
                         }],
                         aliases=['Brilliance U', 'University Brilliance'],
                         acronyms=['UEXC'])), 'UEXC', None), 0.9)
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
                         country={'country_code': 'PR'})), 'UEXC', ['US-PR']),
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
                         country={'country_code': 'AV'})), 'UEXC', ['US-PR']),
            0)


class TestMatchingNode(SimpleTestCase):
    def test_init(self):
        empty = MatchingNode('text')
        self.assertEqual(empty.text, 'text')
        self.assertEqual(empty.children, [])
        self.assertTrue(empty.matched is None)

        node = MatchingNode('text', ['ch1', 'ch2'])
        node.matched = 'obj'
        self.assertEqual(node.text, 'text')
        self.assertEqual(node.children, ['ch1', 'ch2'])
        self.assertEqual(node.matched, 'obj')

    def test_get_children_max_score(self):
        empty = MatchingNode('text')
        self.assertEqual(empty.get_children_max_score(), 0)

        l1 = MatchingNode('l1')
        l1.matched = MatchedOrganization(substring='s1',
                                         score=60,
                                         matching_type='q',
                                         organization='obj')
        l2 = MatchingNode('l2')
        l2.matched = MatchedOrganization(substring='s2',
                                         score=99,
                                         matching_type='q',
                                         organization='obj')
        l3 = MatchingNode('l3')
        l3.matched = MatchedOrganization(substring='s3',
                                         score=42,
                                         matching_type='q',
                                         organization='obj')

        node1 = MatchingNode('text', [l1])
        node1.matched = MatchedOrganization(substring='s2',
                                            score=99,
                                            matching_type='q',
                                            organization='obj')
        self.assertEqual(node1.get_children_max_score(), 60)

        node2 = MatchingNode('text', [l1, l2])
        node2.matched = MatchedOrganization(substring='s3',
                                            score=42,
                                            matching_type='q',
                                            organization='obj')
        self.assertEqual(node2.get_children_max_score(), 99)

        node3 = MatchingNode('text', [node2, l3])
        self.assertEqual(node3.get_children_max_score(), 99)

    def test_remove_descendants_links(self):
        l1 = MatchingNode('l1')
        l1.matched = 'm1'
        l1.remove_descendants_links()
        self.assertEqual(l1.matched, 'm1')

        l1 = MatchingNode('l1')
        l1.matched = 'm1'
        l2 = MatchingNode('l2')
        l2.matched = 'm2'
        node1 = MatchingNode('text', [l1, l2])
        node1.matched = 'm12'
        node1.remove_descendants_links()
        self.assertTrue(l1.matched is None)
        self.assertTrue(l2.matched is None)
        self.assertEqual(node1.matched, 'm12')

        l1 = MatchingNode('l1')
        l1.matched = 'm1'
        l2 = MatchingNode('l2')
        l2.matched = 'm2'
        l3 = MatchingNode('l3')
        l3.matched = 'm3'
        node1 = MatchingNode('text', [l1, l2])
        node1.matched = 'm12'
        node2 = MatchingNode('text', [node1, l3])
        node2.matched = 'm123'
        node2.remove_descendants_links()
        self.assertTrue(l1.matched is None)
        self.assertTrue(l2.matched is None)
        self.assertTrue(l3.matched is None)
        self.assertTrue(node1.matched is None)
        self.assertEqual(node2.matched, 'm123')

    def test_prune_links(self):
        l1 = MatchingNode('l1')
        l1.matched = MatchedOrganization(substring='s1',
                                         score=60,
                                         matching_type='q',
                                         organization='obj')
        l1.prune_links()
        self.assertTrue(l1.matched is not None)

        l1 = MatchingNode('l1')
        l1.matched = MatchedOrganization(substring='s1',
                                         score=60,
                                         matching_type='q',
                                         organization='obj')
        l2 = MatchingNode('l2')
        l2.matched = MatchedOrganization(substring='s2',
                                         score=99,
                                         matching_type='q',
                                         organization='obj')
        l3 = MatchingNode('l3')
        l3.matched = MatchedOrganization(substring='s3',
                                         score=42,
                                         matching_type='q',
                                         organization='obj')
        node1 = MatchingNode('text', [l1, l2])
        node1.matched = MatchedOrganization(substring='s2',
                                            score=99,
                                            matching_type='q',
                                            organization='obj')
        node2 = MatchingNode('text', [node1, l3])
        node2.matched = MatchedOrganization(substring='s3',
                                            score=52,
                                            matching_type='q',
                                            organization='obj')

        node2.prune_links()
        self.assertTrue(l1.matched is not None)
        self.assertTrue(l2.matched is not None)
        self.assertTrue(l3.matched is not None)
        self.assertTrue(node1.matched is not None)
        self.assertTrue(node2.matched is None)

        node3 = MatchingNode('text', [node1, l3])
        node3.matched = MatchedOrganization(substring='s3',
                                            score=100,
                                            matching_type='q',
                                            organization='obj')
        node3.prune_links()
        self.assertTrue(l1.matched is None)
        self.assertTrue(l2.matched is None)
        self.assertTrue(l3.matched is None)
        self.assertTrue(node1.matched is None)
        self.assertTrue(node3.matched is not None)

    def test_get_matching_types(self):
        empty = MatchingNode('text')
        self.assertEqual(len(empty.get_matching_types()), 4)

        node = MatchingNode('text', ['ch1', 'ch2'])
        self.assertEqual(len(node.get_matching_types()), 3)


class TestMatchingGraph(SimpleTestCase):
    def test_init(self):
        graph = MatchingGraph('University of Excellence')
        self.assertEqual(len(graph.nodes), 1)
        self.assertEqual(graph.nodes[0].text, 'University of Excellence')

        graph = \
            MatchingGraph('University of Excellence and Creativity Institute')
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(graph.nodes[0].text, 'University of Excellence')
        self.assertEqual(graph.nodes[1].text, 'Creativity Institute')
        self.assertEqual(graph.nodes[2].text,
                         'University of Excellence and Creativity Institute')

        graph = \
            MatchingGraph('University of Excellence & Creativity Institute')
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(graph.nodes[0].text, 'University of Excellence')
        self.assertEqual(graph.nodes[1].text, 'Creativity Institute')
        self.assertEqual(graph.nodes[2].text,
                         'University of Excellence & Creativity Institute')

        graph = MatchingGraph(
            'University of Excellence &amp; Creativity Institute')
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(graph.nodes[0].text, 'University of Excellence')
        self.assertEqual(graph.nodes[1].text, 'Creativity Institute')
        self.assertEqual(graph.nodes[2].text,
                         'University of Excellence & Creativity Institute')

        graph = MatchingGraph('University of Excellence, Creativity Institute')
        self.assertEqual(len(graph.nodes), 3)
        self.assertEqual(graph.nodes[0].text, 'University of Excellence')
        self.assertEqual(graph.nodes[1].text, 'Creativity Institute')
        self.assertEqual(graph.nodes[2].text,
                         'University of Excellence Creativity Institute')

        graph = MatchingGraph('School of Brilliance, University of ' +
                              'Excellence and Perseverance; 21-100 ' +
                              'Gallifrey: Outerspace')
        self.assertEqual(len(graph.nodes), 11)
        self.assertEqual(graph.nodes[0].text, 'School of Brilliance')
        self.assertEqual(graph.nodes[1].text, 'University of Excellence')
        self.assertEqual(graph.nodes[2].text, 'Perseverance')
        self.assertEqual(graph.nodes[3].text,
                         'University of Excellence and Perseverance')
        self.assertEqual(len(graph.nodes[3].children), 2)
        self.assertEqual(graph.nodes[3].children[0], graph.nodes[1])
        self.assertEqual(graph.nodes[3].children[1], graph.nodes[2])
        self.assertEqual(graph.nodes[4].text,
                         'School of Brilliance University of Excellence')
        self.assertEqual(len(graph.nodes[4].children), 2)
        self.assertEqual(graph.nodes[4].children[0], graph.nodes[0])
        self.assertEqual(graph.nodes[4].children[1], graph.nodes[1])
        self.assertEqual(
            graph.nodes[5].text,
            'School of Brilliance University of Excellence and Perseverance')
        self.assertEqual(len(graph.nodes[5].children), 2)
        self.assertEqual(graph.nodes[5].children[0], graph.nodes[0])
        self.assertEqual(graph.nodes[5].children[1], graph.nodes[3])
        self.assertEqual(graph.nodes[6].text, '21-100 Gallifrey')
        self.assertEqual(graph.nodes[7].text, 'Perseverance 21-100 Gallifrey')
        self.assertEqual(len(graph.nodes[7].children), 2)
        self.assertEqual(graph.nodes[7].children[0], graph.nodes[2])
        self.assertEqual(graph.nodes[7].children[1], graph.nodes[6])
        self.assertEqual(
            graph.nodes[8].text,
            'University of Excellence and Perseverance 21-100 Gallifrey')
        self.assertEqual(len(graph.nodes[8].children), 2)
        self.assertEqual(graph.nodes[8].children[0], graph.nodes[3])
        self.assertEqual(graph.nodes[8].children[1], graph.nodes[6])
        self.assertEqual(graph.nodes[9].text, 'Outerspace')
        self.assertEqual(graph.nodes[10].text, '21-100 Gallifrey Outerspace')
        self.assertEqual(len(graph.nodes[10].children), 2)
        self.assertEqual(graph.nodes[10].children[0], graph.nodes[6])
        self.assertEqual(graph.nodes[10].children[1], graph.nodes[9])

    def test_remove_low_scores(self):
        graph = MatchingGraph('University of Excellence, Creativity Institute')
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

    def test_prune_links(self):
        graph = MatchingGraph('School of Brilliance, University of ' +
                              'Excellence and Perseverance; 21-100 ' +
                              'Gallifrey: Outerspace')
        graph.nodes[0].matched = MatchedOrganization(substring='s0',
                                                     score=10,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[1].matched = MatchedOrganization(substring='s1',
                                                     score=80,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[2].matched = MatchedOrganization(substring='s2',
                                                     score=0,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[3].matched = MatchedOrganization(substring='s3',
                                                     score=100,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[4].matched = MatchedOrganization(substring='s4',
                                                     score=50,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[5].matched = MatchedOrganization(substring='s5',
                                                     score=47,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[6].matched = MatchedOrganization(substring='s6',
                                                     score=5,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[7].matched = MatchedOrganization(substring='s7',
                                                     score=15,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[8].matched = MatchedOrganization(substring='s8',
                                                     score=7,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[9].matched = MatchedOrganization(substring='s9',
                                                     score=60,
                                                     matching_type='q',
                                                     organization='obj')
        graph.nodes[10].matched = MatchedOrganization(substring='sa',
                                                      score=30,
                                                      matching_type='q',
                                                      organization='obj')

        graph.prune_links()

        self.assertTrue(graph.nodes[0].matched is None)
        self.assertTrue(graph.nodes[1].matched is None)
        self.assertTrue(graph.nodes[2].matched is None)
        self.assertTrue(graph.nodes[3].matched is not None)
        self.assertTrue(graph.nodes[3].matched.substring, 's3')
        self.assertTrue(graph.nodes[4].matched is not None)
        self.assertTrue(graph.nodes[4].matched.substring, 's4')
        self.assertTrue(graph.nodes[5].matched is None)
        self.assertTrue(graph.nodes[6].matched is None)
        self.assertTrue(graph.nodes[7].matched is not None)
        self.assertTrue(graph.nodes[7].matched.substring, 's7')
        self.assertTrue(graph.nodes[8].matched is None)
        self.assertTrue(graph.nodes[9].matched is not None)
        self.assertTrue(graph.nodes[9].matched.substring, 's9')
        self.assertTrue(graph.nodes[10].matched is None)


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

        c1_ch = self.org('s 1', 1, MATCHING_TYPE_PHRASE, 'org1', chosen=True)
        c2_ch = self.org('s 2', 0.94, MATCHING_TYPE_FUZZY, 'org2', chosen=True)

        self.assertEquals(
            get_output(
                [c1, c2],
                [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10, m11, m12, m13]),
            [c1_ch, c2_ch, m10, m7, m11])
