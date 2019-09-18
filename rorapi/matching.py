import os
import re
import unidecode

from .es_utils import ESQueryBuilder
from .models import MatchingResult, Errors

from collections import namedtuple
from functools import lru_cache
from fuzzywuzzy import fuzz
from itertools import groupby

MIN_MATCHING_SCORE = 0.9

MATCHING_TYPE_PHRASE = 'PHRASE'
MATCHING_TYPE_COMMON = 'COMMON TERMS'
MATCHING_TYPE_FUZZY = 'FUZZY'
MATCHING_TYPE_HEURISTICS = 'HEURISTICS'
MATCHING_TYPE_ACRONYM = 'ACRONYM'

#####################################################################
# Country extraction                                                #
#####################################################################


@lru_cache(maxsize=None)
def load_countries():
    '''Load code-name map from the file'''

    countries = []
    with open(os.path.join(os.path.split(__file__)[0],
                           'countries.txt')) as file:
        lines = [line.strip().split() for line in file]
        countries = [(line[0], ' '.join(line[1:])) for line in lines]
    return countries


COUNTRIES = load_countries()


def to_region(c):
    '''Map country code to "region" string.

    This effectively groups countries often confused in the data to make sure
    the scoring functions do not reject potential matching candidates.'''

    return {
        'GB': 'GB-UK',
        'UK': 'GB-UK',
        'CN': 'CN-HK-TW',
        'HK': 'CN-HK-TW',
        'TW': 'CN-HK-TW',
        'PR': 'US-PR',
        'US': 'US-PR'
    }.get(c, c)


def get_country_codes(string):
    '''Extract the country codes from the string,
    if the country names are mentioned.'''

    string = unidecode.unidecode(string).strip()
    lower = re.sub(r'\s+', ' ', string.lower())
    lower_alpha = re.sub(r'\s+', ' ', re.sub('[^a-z]', ' ', string.lower()))
    alpha = re.sub(r'\s+', ' ', re.sub('[^a-zA-Z]', ' ', string))
    codes = []
    for code, name in COUNTRIES:
        if re.search('[^a-z]', name):
            score = fuzz.partial_ratio(name, lower)
        elif len(name) == 2:
            score = max([fuzz.ratio(name.upper(), t) for t in alpha.split()])
        else:
            score = max([fuzz.ratio(name, t) for t in lower_alpha.split()])
        if score >= 90:
            codes.append(code.upper())
    return list(set(codes))


def get_countries(string):
    '''Extract country codes the the string and map to regions.'''

    codes = get_country_codes(string)
    return [to_region(c) for c in codes]


#####################################################################
# Similarity                                                        #
#####################################################################


def normalize(s):
    '''Normalize string for matching.'''

    s = re.sub(r'\s+', ' ', unidecode.unidecode(s).strip().lower())
    s = re.sub(
        '(?<![a-z])univ$', 'university',
        re.sub(r'(?<![a-z])univ[\. ]', 'university ',
               re.sub(r'(?<![a-z])u\.(?! ?[a-z]\.)', 'university ', s)))
    s = re.sub('(?<![a-z])lab$', 'laboratory',
               re.sub('(?<![a-z])lab[^a-z]', 'laboratory ', s))
    s = re.sub('(?<![a-z])inst$', 'institute',
               re.sub('(?<![a-z])inst[^a-z]', 'institute ', s))
    s = re.sub('(?<![a-z])tech$', 'technology',
               re.sub('(?<![a-z])tech[^a-z]', 'technology ', s))
    s = re.sub(r'(?<![a-z])u\. ?s\.', 'united states', s)
    s = re.sub('&', ' and ', re.sub('&amp;', ' and ', s))
    s = re.sub('^the ', '', s)
    s = re.sub(r'\s+', ' ', s.strip().lower())
    return s


def get_similarity(aff_sub, cand_name):
    '''Calculate the similarity between the affiliation substring
    and the candidate name version.'''

    aff_sub = normalize(aff_sub)
    cand_name = normalize(cand_name)
    comparfun = fuzz.token_sort_ratio
    if '(' in aff_sub or ')' in aff_sub or '-' in aff_sub or \
        len([s for s in ['university', 'college', 'school', 'department',
                         'institute', 'center', 'hospital']
             if s in aff_sub]) > 1:
        comparfun = fuzz.partial_ratio
    cand_name = re.sub(r'\(.*\)', '', cand_name).strip()
    if min(len(aff_sub), len(cand_name)) < 12:
        return 1 if aff_sub == cand_name else 0
    return comparfun(aff_sub, cand_name) / 100


def get_score(candidate, aff_sub, countries):
    '''Calculate the similarity between the affiliation substring
    and the candidate, using all name versions.'''

    if countries and \
            to_region(candidate.country.country_code) not in countries:
        return 0
    scores = [
        get_similarity(aff_sub, c) for c in [candidate.name] +
        [l.label for l in candidate.labels] + list(candidate.aliases)
    ]
    if aff_sub != 'USA' and aff_sub in candidate.acronyms:
        scores.append(1) if countries else scores.append(0.9)
    return max(scores)


#####################################################################
# Matching                                                          #
#####################################################################

MatchedOrganization = namedtuple(
    'MatchedOrganization',
    ['chosen', 'substring', 'matching_type', 'score', 'organization'])
MatchedOrganization.__new__.__defaults__ = (False, None, None, 0, None)


def match_by_query(text, matching_type, query, countries):
    '''Match affiliation text using specific ES query.'''

    candidates = query.execute()
    scores = [(candidate, get_score(candidate, text, countries))
              for candidate in candidates]
    if not candidates:
        return MatchedOrganization(substring=text,
                                   matching_type=matching_type), []
    max_score = max([s[1] for s in scores])
    best = [s for s in scores if s[1] == max_score][0]
    chosen = MatchedOrganization(substring=text,
                                 matching_type=matching_type,
                                 score=best[1],
                                 organization=best[0])
    all_matched = [
        MatchedOrganization(substring=text,
                            matching_type=matching_type,
                            score=s,
                            organization=c) for c, s in scores
    ]
    return chosen, all_matched


def match_by_type(text, matching_type, countries):
    '''Match affiliation text using specific matching mode/type.'''

    fields = ['name.norm', 'aliases.norm', 'labels.label.norm']
    substrings = []
    if matching_type == MATCHING_TYPE_HEURISTICS:
        h1 = re.search(r'University of ([^\s]+)', text)
        if h1 is not None:
            substrings.append(h1.group())
            substrings.append(h1.group(1) + ' University')
        h2 = re.search(r'([^\s]+) University', text)
        if h2 is not None:
            substrings.append(h2.group())
            substrings.append('University of ' + h2.group(1))
    elif matching_type == MATCHING_TYPE_ACRONYM:
        substrings = re.findall('[A-Z]{3,}', text)
    else:
        substrings.append(text)

    queries = [ESQueryBuilder() for _ in substrings]
    for s, q in zip(substrings, queries):
        if matching_type == MATCHING_TYPE_PHRASE:
            q.add_phrase_query(fields, normalize(text))
        elif matching_type == MATCHING_TYPE_COMMON:
            q.add_common_query(fields, normalize(text))
        elif matching_type == MATCHING_TYPE_FUZZY:
            q.add_fuzzy_query(fields, normalize(text))
        elif matching_type == MATCHING_TYPE_ACRONYM:
            q.add_match_query(normalize(text))
        elif matching_type == MATCHING_TYPE_HEURISTICS:
            q.add_common_query(fields, normalize(text))
    queries = [q.get_query() for q in queries]

    matched = [
        match_by_query(t, matching_type, q, countries)
        for t, q in zip(substrings, queries)
    ]
    if not matched:
        matched.append((MatchedOrganization(substring=text,
                                            matching_type=matching_type), []))
    all_matched = [m for sub in matched for m in sub[1]]
    max_score = max([m[0].score for m in matched])
    chosen = [m[0] for m in matched if m[0].score == max_score][0]
    return chosen, all_matched


class MatchingNode:
    '''Matching node class. Represents a substring of the original affiliation
    that potentially could be matched to an organization.'''
    def __init__(self, text, children=[]):
        self.text = text
        self.children = children
        self.matched = None
        self.all_matched = []

    def get_children_max_score(self):
        score = 0
        for child in self.children:
            if child.matched is not None and child.matched.score > score:
                score = child.matched.score
            child_tree_score = child.get_children_max_score()
            if child_tree_score > score:
                score = child_tree_score
        return score

    def remove_descendants_links(self):
        for child in self.children:
            child.matched = None
            child.remove_descendants_links()

    def prune_links(self):
        if self.matched is None:
            return
        children_max_score = self.get_children_max_score()
        if children_max_score >= self.matched.score:
            self.matched = None
        else:
            self.remove_descendants_links()

    def get_matching_types(self):
        if self.children:
            return [
                MATCHING_TYPE_PHRASE, MATCHING_TYPE_COMMON, MATCHING_TYPE_FUZZY
            ]
        else:
            return [
                MATCHING_TYPE_PHRASE, MATCHING_TYPE_COMMON,
                MATCHING_TYPE_FUZZY, MATCHING_TYPE_HEURISTICS
            ]

    def match(self, countries, min_score):
        for matching_type in self.get_matching_types():
            chosen, all_matched = match_by_type(self.text, matching_type,
                                                countries)
            self.all_matched.extend(all_matched)
            if self.matched is None:
                self.matched = chosen
            if self.matched is not None and chosen.score > self.matched.score \
                    and self.matched.score < min_score:
                self.matched = chosen


class MatchingGraph:
    '''A matching graph represents the entire input affiliation. The nodes
    are substrings that could be potentially matched to an organization name.
    Some substrings contain other substrings, which defines the graph edges.
    This prevents matching an organization to a substring and another
    organization to the substring's substring.'''
    def __init__(self, affiliation):
        self.nodes = []
        self.affiliation = affiliation
        affiliation = re.sub('&amp;', '&', affiliation)
        prev = []
        for part in [s.strip() for s in re.split('[,;:]', affiliation)]:
            part_norm = re.sub(' and ', ' & ', part)
            if '&' in part_norm:
                part1 = re.sub('&.*', '', part_norm).strip()
                part2 = re.sub('.*&', '', part_norm).strip()
                n1 = MatchingNode(part1)
                n2 = MatchingNode(part2)
                nn = MatchingNode(part, [n1, n2])
                self.nodes.append(n1)
                self.nodes.append(n2)
                self.nodes.append(nn)
                for p in prev:
                    self.nodes.append(
                        MatchingNode(p.text + ' ' + part1, [p, n1]))
                    self.nodes.append(
                        MatchingNode(p.text + ' ' + part, [p, nn]))
                prev = [n2, nn]
            else:
                n = MatchingNode(part)
                self.nodes.append(n)
                for p in prev:
                    self.nodes.append(MatchingNode(p.text + ' ' + part,
                                                   [p, n]))
                prev = [n]

    def remove_low_scores(self, min_score):
        for node in self.nodes:
            if node.matched is not None and node.matched.score < min_score:
                node.matched = None

    def prune_links(self):
        for node in self.nodes:
            node.prune_links()

    def match(self, countries, min_score):
        for node in self.nodes:
            node.match(countries, min_score)
        self.remove_low_scores(min_score)
        self.prune_links()
        chosen = []
        all_matched = []
        for node in self.nodes:
            all_matched.extend(node.all_matched)
            if node.matched is not None and \
                node.matched.organization['id'] not in [m.organization['id']
                                                        for m in chosen]:
                chosen.append(node.matched)
        acr_chosen, acr_all_matched = match_by_type(self.affiliation,
                                                    MATCHING_TYPE_ACRONYM,
                                                    countries)
        all_matched.extend(acr_all_matched)
        if not chosen and acr_chosen.score >= min_score:
            chosen.append(acr_chosen)
        return chosen, all_matched


def get_output(chosen, all_matched):
    type_map = {
        MATCHING_TYPE_PHRASE: 4,
        MATCHING_TYPE_COMMON: 3,
        MATCHING_TYPE_FUZZY: 2,
        MATCHING_TYPE_HEURISTICS: 1,
        MATCHING_TYPE_ACRONYM: 0
    }
    output = []
    all_matched = [m for m in all_matched if m.score > 0]
    all_matched = sorted(all_matched, key=lambda x: x.organization.id)
    for _, g in groupby(all_matched, lambda x: x.organization.id):
        g = list(g)
        best = g[0]
        for c in g:
            if c in chosen:
                best = MatchedOrganization(substring=c.substring,
                                           score=c.score,
                                           chosen=True,
                                           matching_type=c.matching_type,
                                           organization=c.organization)
                break
            if best.score < c.score:
                best = c
            if best.score == c.score and \
                    type_map[best.matching_type] < type_map[c.matching_type]:
                best = c
            if best.score == c.score and \
                    type_map[best.matching_type] == type_map[c.matching_type] \
                    and len(best.substring) > len(c.substring):
                best = c
        output.append(best)
    return sorted(output, key=lambda x: x.score, reverse=True)[:100]


def match_affiliation(affiliation):
    countries = get_countries(affiliation)
    graph = MatchingGraph(affiliation)
    chosen, all_matched = graph.match(countries, MIN_MATCHING_SCORE)
    return get_output(chosen, all_matched)


def match_organizations(params):
    if 'affiliation' in params:
        matched = match_affiliation(params.get('affiliation'))
        return None, MatchingResult(matched)
    return Errors('"affiliation" parameter missing'), None
