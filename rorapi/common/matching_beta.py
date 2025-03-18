import geonamescache
import os
import re
import unicodedata
import unidecode

from rorapi.common.models import Errors
from rorapi.common.es_utils import ESQueryBuilder
from rorapi.v1.models import MatchingResult as MatchingResultV1
from rorapi.v2.models import MatchingResult as MatchingResultV2

from collections import namedtuple
from functools import lru_cache
from rapidfuzz import fuzz
from itertools import groupby

MIN_CHOSEN_SCORE = 92
MIN_SCORE = 50

MATCHING_TYPE_PHRASE = "PHRASE"
MATCHING_TYPE_COMMON = "COMMON TERMS"
MATCHING_TYPE_FUZZY = "FUZZY"
MATCHING_TYPE_HEURISTICS = "HEURISTICS"
MATCHING_TYPE_ACRONYM = "ACRONYM"
MATCHING_TYPE_EXACT = "EXACT"
MATCHING_TYPE_SINGLE = "SINGLE SEARCH"

NODE_MATCHING_TYPES = (
    MATCHING_TYPE_PHRASE,
    MATCHING_TYPE_COMMON,
    MATCHING_TYPE_FUZZY,
    MATCHING_TYPE_HEURISTICS,
)

SPECIAL_CHARS_REGEX = '[\+\-\=\|\>\<\!\(\)\\\{\}\[\]\^"\~\*\?\:\/\.\,\;]'
DO_NOT_MATCH = "university hospital"

#####################################################################
# Country extraction                                                #
#####################################################################


@lru_cache(maxsize=None)
def load_geonames_countries():
    """Load countries from geonames"""
    gc = geonamescache.GeonamesCache()
    gc_countries = gc.get_countries()
    return gc_countries


GEONAMES_COUNTRIES = load_geonames_countries()


@lru_cache(maxsize=None)
def load_geonames_cities():
    """Load countries with population > 15000 from geonames"""
    gc = geonamescache.GeonamesCache()
    gc_cities = gc.get_cities()
    return gc_cities


GEONAMES_CITIES = load_geonames_cities()


@lru_cache(maxsize=None)
def load_countries():
    """Load custom country code map from countries.txt"""

    countries = []
    with open(os.path.join(os.path.split(__file__)[0], "countries.txt")) as file:
        lines = [line.strip().split() for line in file]
        countries = [(line[0], " ".join(line[1:])) for line in lines]
    return countries


COUNTRIES = load_countries()


def to_region(c):
    """Map country code to "region" string.

    This effectively groups countries often confused in the data to make sure
    the scoring functions do not reject potential matching candidates."""

    return {
        "GB": "GB-UK",
        "UK": "GB-UK",
        "CN": "CN-HK-TW",
        "HK": "CN-HK-TW",
        "TW": "CN-HK-TW",
        "PR": "US-PR",
        "US": "US-PR",
    }.get(c, c)


def get_country_codes(string):
    string = unidecode.unidecode(string).strip()
    lower = re.sub(r"\s+", " ", string.lower())
    lower_alpha = re.sub(r"\s+", " ", re.sub("[^a-z]", " ", string.lower()))
    alpha = re.sub(r"\s+", " ", re.sub("[^a-zA-Z]", " ", string))
    codes = []
    for code, name in GEONAMES_COUNTRIES:
        if re.search("[^a-z]", name):
            score = fuzz.partial_ratio(name, lower)
        elif len(name) == 2:
            score = max([fuzz.ratio(name.upper(), t) for t in alpha.split()] + [0])
        else:
            score = max([fuzz.ratio(name, t) for t in lower_alpha.split()] + [0])
        if score >= 90:
            codes.append(code.upper())
    return list(set(codes))



def get_countries(string):
    """Extract country codes the the string and map to regions."""

    codes = get_country_codes(string)
    return [to_region(c) for c in codes]


#####################################################################
# Similarity                                                        #
#####################################################################


def check_latin_chars(s):
    for ch in s:
        if ch.isalpha():
            if "LATIN" not in unicodedata.name(ch):
                return False
    return True


def normalize(s):
    """Normalize string for matching."""

    if check_latin_chars(s):
        s = re.sub(r"\s+", " ", unidecode.unidecode(s).strip().lower())
    else:
        s = re.sub(r"\s+", " ", s.strip().lower())
    s = re.sub(
        "(?<![a-z])univ$",
        "university",
        re.sub(
            r"(?<![a-z])univ[\. ]",
            "university ",
            re.sub(r"(?<![a-z])u\.(?! ?[a-z]\.)", "university ", s),
        ),
    )
    s = re.sub(
        "(?<![a-z])lab$",
        "laboratory",
        re.sub("(?<![a-z])lab[^a-z]", "laboratory ", s),
    )
    s = re.sub(
        "(?<![a-z])inst$",
        "institute",
        re.sub("(?<![a-z])inst[^a-z]", "institute ", s),
    )
    s = re.sub(
        "(?<![a-z])tech$",
        "technology",
        re.sub("(?<![a-z])tech[^a-z]", "technology ", s),
    )
    s = re.sub(r"(?<![a-z])u\. ?s\.", "united states", s)
    s = re.sub("&", " and ", re.sub("&amp;", " and ", s))
    s = re.sub("^the ", "", s)
    s = re.sub(r"\s+", " ", s.strip().lower())
    return s

def get_similarity(aff_sub, cand_name):
    """Calculate the similarity between the affiliation substring
    and the candidate name version."""

    aff_sub = normalize(aff_sub)
    cand_name = normalize(cand_name)
    comparfun = fuzz.token_sort_ratio
    if (
        "(" in aff_sub
        or ")" in aff_sub
        or "-" in aff_sub
        or len(
            [
                s
                for s in [
                    "university",
                    "college",
                    "school",
                    "department",
                    "institute",
                    "center",
                    "hospital",
                ]
                if s in aff_sub
            ]
        )
        > 1
    ):
        comparfun = fuzz.partial_ratio
    cand_name = re.sub(r"\(.*\)", "", cand_name).strip()
    return comparfun(aff_sub, cand_name) / 100


def get_score(candidate, aff_sub, countries, version):
    """Calculate the similarity between the affiliation substring
    and the candidate, using all name versions."""
    if version == "v2":
        country_code = candidate.locations[0].geonames_details.country_code
        all_names = [
            name["value"] for name in candidate.names if "acronym" not in name["types"]
        ]
        acronyms = [
            name["value"] for name in candidate.names if "acronym" in name["types"]
        ]
    else:
        country_code = candidate.country.country_code
        all_names = (
            [candidate.name]
            + [l.label for l in candidate.labels]
            + list(candidate.aliases)
        )
        acronyms = candidate.acronyms

    if countries and to_region(country_code) not in countries:
        return 0
    scores = [get_similarity(aff_sub, name) for name in all_names]
    if aff_sub != "USA" and aff_sub in acronyms:
        scores.append(1) if countries else scores.append(0.9)
    return max(scores)


### begin new search functions
def check_latin_chars(s):
    for ch in s:
        if ch.isalpha():
            if "LATIN" not in unicodedata.name(ch):
                return False
    return True


def last_non_overlapping(candidates):
    matched = None
    for candidate in candidates:
        overlap = False
        for other in candidates:
            if candidate.organization["_id"] == other.organization["_id"]:
                continue
            if (
                candidate.start <= other.start <= candidate.end
                or candidate.start <= other.end <= candidate.end
                or other.start <= candidate.start <= other.end
                or other.start <= candidate.end <= other.end
            ):
                overlap = True
        if not overlap:
            matched = candidate
    return matched


def is_better(aff, candidate, other):
    score = 0
    if "univ" in candidate.name.lower() and "univ" not in other.name.lower():
        score += 1
    if "univ" not in candidate.name.lower() and "univ" in other.name.lower():
        score -= 1
    c_diff = abs(len(candidate.name) - len(aff))
    o_diff = abs(len(other.name) - len(aff))
    if o_diff - c_diff > 4:
        score += 1
    if c_diff - o_diff > 4:
        score -= 1
    if candidate.start > other.end:
        score += 1
    if other.start > candidate.end:
        score -= 1
    if candidate.score > 99 and other.score < 99:
        score += 1
    if candidate.score < 99 and other.score > 99:
        score -= 1
    return score > 0


def rescore(aff, candidates):
    new_scores = []
    for candidate in candidates:
        ns = 0
        for other in candidates:
            if is_better(aff, candidate, other):
                ns += 1
        new_scores.append(ns)
    print(new_scores)
    return [c._replace(rescore=ns) for c, ns in zip(candidates, new_scores)]


def choose_candidate(rescored):
    top_score = max([c.rescore for c in rescored])
    print("Top score")
    print(top_score)
    top_scored = [c for c in rescored if c.rescore == top_score]
    print("Top scored")
    print(top_scored)

    if len(top_scored) == 1:
        return top_scored[0]
    print(last_non_overlapping(top_scored))
    return last_non_overlapping(top_scored)


def score(aff, candidate):
    best = MatchedOrganization(
        organization=candidate, name="", score=0, rescore=0, start=-1, end=-1, matching_type=MATCHING_TYPE_SINGLE, substring=aff, chosen=False
    )
    for candidate_name in candidate["_source"]["search"]["names_ids"]:
        if hasattr(candidate_name, "name"):
            name = candidate_name["name"]
            if (
                name.lower() in ["university school", "university hospital"]
                or len(name) >= len(aff) + 4
                or len(name) < 5
                or (" " not in name and aff.lower() != name.lower())
                or (" " not in aff and aff.lower() != name.lower())
            ):
                continue
            alignment = fuzz.partial_ratio_alignment(
                normalize(aff), normalize(name)
            )
            if alignment.score > best.score:
                best = MatchedOrganization(
                    organization=candidate,
                    name=name,
                    score=alignment.score,
                    rescore=alignment.score,
                    start=alignment.src_start,
                    end=alignment.src_end,
                    matching_type=MATCHING_TYPE_SINGLE,
                    substring=aff,
                    chosen=False
                )
    return best



#####################################################################
# Matching                                                          #
#####################################################################

MatchedOrganization = namedtuple(
    "MatchedOrganization",
    ["organization", "name", "score", "rescore", "start", "end", "matching_type", "substring", "chosen"],
)
MatchedOrganization.__new__.__defaults__ = (None, None, 0, 0, 0, 0, None, None, False)


def match_by_query(text, matching_type, query, countries, version):
    """Match affiliation text using specific ES query."""
    scored_candidates = []
    chosen_candidate = None
    chosen_true = None
    results = query.execute()
    candidates = results.hits.hits
    if candidates:
        scored_candidates = [score(text, c) for c in candidates]
        scored_candidates = [s for s in scored_candidates if s.score >= MIN_SCORE]
        for s in scored_candidates:
            print(f'score: {s.score}')
        if scored_candidates:
            if len(scored_candidates) == 1:
                chosen_candidate = scored_candidates[0]
            if len(scored_candidates) > 1:
                rescored_candidates = rescore(text, scored_candidates)
                rescored_candidates = [r for r in rescored_candidates if r.score >= MIN_CHOSEN_SCORE]
                if rescored_candidates:
                    chosen_candidate = choose_candidate(rescored_candidates)
            if chosen_candidate:
                print("Chosen:")
                print(chosen_candidate)
                chosen_true  = MatchedOrganization(
                    organization=chosen_candidate.organization,
                    name=chosen_candidate.name,
                    rescore=chosen_candidate.rescore,
                    score=round(chosen_candidate.score / 100, 2),
                    start=chosen_candidate.start,
                    end=chosen_candidate.end,
                    matching_type=MATCHING_TYPE_SINGLE,
                    substring=chosen_candidate.substring,
                    chosen=True
                )
        scored_candidates = [s._replace(score = round(s.score / 100, 2)) for s in scored_candidates]

    return chosen_true, scored_candidates


def match_by_type(text, matching_type, countries, version):
    """Match affiliation text using specific matching mode/type."""

    fields_v1 = ["name.norm", "aliases.norm", "labels.label.norm"]
    fields_v2 = ["names.value.norm"]
    substrings = []
    if matching_type == MATCHING_TYPE_HEURISTICS:
        h1 = re.search(r"University of ([^\s]+)", text)
        if h1 is not None:
            substrings.append(h1.group())
            substrings.append(h1.group(1) + " University")
        h2 = re.search(r"([^\s]+) University", text)
        if h2 is not None:
            substrings.append(h2.group())
            substrings.append("University of " + h2.group(1))
    elif matching_type == MATCHING_TYPE_ACRONYM:
        iso3_substrings = []
        all_substrings = re.findall("[A-Z]{3,}", text)
        for substring in all_substrings:
            for country in GEONAMES_COUNTRIES.values():
                if substring.lower() == country["iso3"].lower():
                    iso3_substrings.append(substring)
        substrings = [x for x in all_substrings if x not in iso3_substrings]

    else:
        substrings.append(text)

    queries = [ESQueryBuilder(version) for _ in substrings]

    if version == "v2":
        fields = fields_v2
    else:
        fields = fields_v1

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
        match_by_query(t, matching_type, q, countries, version)
        for t, q in zip(substrings, queries)
    ]
    if not matched:
        matched.append(
            (MatchedOrganization(substring=text, matching_type=matching_type), [])
        )
    all_matched = [m for sub in matched for m in sub[1]]
    max_score = max([m[0].score for m in matched])
    chosen = [m[0] for m in matched if m[0].score == max_score][0]

    return chosen, all_matched


class MatchingNode:
    """Matching node class. Represents a substring of the original affiliation
    that potentially could be matched to an organization."""

    def __init__(self, text, version):
        self.text = text
        self.version = version
        self.matched = None
        self.all_matched = []

    def match(self, countries, min_score):
        for matching_type in NODE_MATCHING_TYPES:
            chosen, all_matched = match_by_type(
                self.text, matching_type, countries, self.version
            )
            self.all_matched.extend(all_matched)
            if self.matched is None:
                self.matched = chosen
            if (
                self.matched is not None
                and chosen.score > self.matched.score
                and self.matched.score < min_score
            ):
                self.matched = chosen


def clean_search_string(search_string):
    # strip special chars
    search_string_cleaned = re.sub(SPECIAL_CHARS_REGEX, " ", search_string)
    # replace multiple spaces with 1 space
    search_string_cleaned = re.sub(" +", " ", search_string_cleaned)
    search_string_cleaned = search_string_cleaned.strip()
    # strip postal codes
    search_string_cleaned = re.sub("\d{5}", "", search_string_cleaned)
    return search_string_cleaned


def check_do_not_match(search_string):
    do_not_match = False
    if search_string.lower() in DO_NOT_MATCH:
        do_not_match = True
        return do_not_match
    else:
        for country in GEONAMES_COUNTRIES.values():
            if (
                search_string.lower() == country["name"].lower()
                or search_string.lower() == country["iso"].lower()
                or search_string.lower() == country["iso3"].lower()
            ):
                do_not_match = True
                break
        for city in GEONAMES_CITIES.values():
            if search_string.lower() == city["name"].lower():
                do_not_match = True
                break
    return do_not_match


class MatchingGraph:
    """A matching graph represents the entire input affiliation. The nodes
    are substrings that could be potentially matched to an organization name.
    Some substrings contain other substrings, which defines the graph edges.
    This prevents matching an organization to a substring and another
    organization to the substring's substring."""

    def __init__(self, affiliation, version):
        self.nodes = []
        self.version = version
        self.affiliation = affiliation
        affiliation = re.sub("&amp;", "&", affiliation)
        affiliation_cleaned = clean_search_string(affiliation)
        n = MatchingNode(affiliation_cleaned, self.version)
        self.nodes.append(n)
        for part in [s.strip() for s in re.split("[,;:]", affiliation)]:
            part_cleaned = clean_search_string(part)
            do_not_match = check_do_not_match(part_cleaned)
            # do not perform search if substring exactly matches a country name or ISO code
            if do_not_match == False:
                n = MatchingNode(part_cleaned, self.version)
                self.nodes.append(n)

    def remove_low_scores(self, min_score):
        for node in self.nodes:
            if node.matched is not None and node.matched.score < min_score:
                node.matched = None

    def match(self, countries, min_score):
        for node in self.nodes:
            node.match(countries, min_score)
        self.remove_low_scores(min_score)
        chosen = []
        all_matched = []
        for node in self.nodes:
            all_matched.extend(node.all_matched)
            if node.matched is not None and node.matched.organization["id"] not in [
                m.organization["id"] for m in chosen
            ]:
                chosen.append(node.matched)
        acr_chosen, acr_all_matched = match_by_type(
            self.affiliation, MATCHING_TYPE_ACRONYM, countries, self.version
        )
        all_matched.extend(acr_all_matched)
        return chosen, all_matched


def get_output(chosen, all_matched, active_only):
    #all_matched = [m for m in all_matched if m.rescore > MIN_MATCHING_SCORE]
    if active_only:
        all_matched = [m for m in all_matched if m.organization['_source']['status'] == "active"]
    all_matched = sorted(all_matched, key=lambda x: x.score, reverse=True)[:100]
    if chosen:
        all_matched = [a for a in all_matched if a.organization['_id'] != chosen.organization['_id']]
        all_matched.insert(0, chosen)
    return all_matched


def check_exact_match(affiliation, countries, version):
    qb = ESQueryBuilder(version)
    qb.add_string_query('"' + affiliation + '"')
    return match_by_query(
        affiliation, MATCHING_TYPE_EXACT, qb.get_query(), countries, version
    )

def check_exact_match(affiliation, countries, version):
    qb = ESQueryBuilder(version)
    qb.add_string_query('"' + affiliation + '"')
    return match_by_query(
        affiliation, MATCHING_TYPE_EXACT, qb.get_query(), countries, version
    )

def get_candidates(aff, countries, version):
    qb = ESQueryBuilder(version)
    qb.add_string_query(aff)
    return match_by_query(
        aff, MATCHING_TYPE_SINGLE, qb.get_query(), countries, version
    )

def match_affiliation(affiliation, active_only, version):
    countries = get_countries(affiliation)
    chosen, all_matched = get_candidates(affiliation, countries, version)
    return get_output(chosen, all_matched, active_only)


def match_organizations(params, version):
    if "affiliation" in params:
        active_only = True
        if "all_status" in params:
            if params["all_status"] == "" or params["all_status"].lower() == "true":
                active_only = False
        matched = match_affiliation(params.get("affiliation"), active_only, version)
        if version == "v2":
            return None, MatchingResultV2(matched)
        return None, MatchingResultV1(matched)
    return Errors('"affiliation" parameter missing'), None
