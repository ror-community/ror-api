import geonamescache
import os
import re
import unicodedata
import unidecode
from rorapi.settings import ES7, ES_VARS
from elasticsearch_dsl import Search, Q

from rorapi.common.models import Errors
from rorapi.common.es_utils import ESQueryBuilder
from rorapi.v1.models import MatchingResult as MatchingResultV1
from rorapi.v2.models import MatchingResult as MatchingResultV2

from collections import namedtuple
from functools import lru_cache
from rapidfuzz import fuzz
from itertools import groupby

INDEX = ES_VARS["INDEX_V2"]
MAX_CANDIDATES = 200
MIN_SCORE = 96


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

CandidateMatch = namedtuple(
    "CandidateMatch",
    ["candidate", "name", "score", "start", "end"],
)


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
    """Extract the country codes from the string,
    if the country names are mentioned."""

    string = unidecode.unidecode(string).strip()
    lower = re.sub(r"\s+", " ", string.lower())
    lower_alpha = re.sub(r"\s+", " ", re.sub("[^a-z]", " ", string.lower()))
    alpha = re.sub(r"\s+", " ", re.sub("[^a-zA-Z]", " ", string))
    codes = []
    for code, name in COUNTRIES:
        if re.search("[^a-z]", name):
            score = fuzz.partial_ratio(name, lower)
        elif len(name) == 2:
            score = max([fuzz.ratio(name.upper(), t) for t in alpha.split()])
        else:
            score = max([fuzz.ratio(name, t) for t in lower_alpha.split()])
        if score >= 90:
            codes.append(code.upper())
    return list(set(codes))


def get_countries(string):
    """Extract country codes the the string and map to regions."""

    codes = get_country_codes(string)
    return [to_region(c) for c in codes]


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
            if candidate.candidate["_id"] == other.candidate["_id"]:
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
    return [c._replace(score=ns) for c, ns in zip(candidates, new_scores)]


def choose_candidate(aff, candidates):
    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    rescored = rescore(aff, candidates)
    top_score = max([c.score for c in rescored])
    top_scored = [c for c in rescored if c.score == top_score]

    if len(top_scored) == 1:
        return top_scored[0]

    return last_non_overlapping(top_scored)


def score(aff, candidate):
    best = CandidateMatch(
        candidate=candidate, name="", score=0, start=-1, end=-1
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
                best = CandidateMatch(
                    candidate=candidate,
                    name=name,
                    score=alignment.score,
                    start=alignment.src_start,
                    end=alignment.src_end,
                )
    return best



def get_candidates(aff):
    qb = ESQueryBuilder("v2")
    qb.add_string_query(aff)
    search = qb.get_query()
    results = search.execute()
    return results.hits.hits


def match(input_data, active_only):
    aff_countries = get_countries(input_data)
    candidates = get_candidates(input_data)
    if active_only:
        candidates = [
            c
            for c in candidates
            if c["_source"]["status"] == "active"
        ]

    candidates = [score(input_data, c) for c in candidates]
    candidates = [c for c in candidates if c.score >= MIN_SCORE]


    matched = choose_candidate(input_data, candidates)
    if matched is None:
        return []
    if (
        aff_countries
        and to_region(
            matched.candidate["_source"]["locations"][0]["geonames_details"]["country_code"]
        )
        not in aff_countries
    ):
        return []
    return [
        {
            "id": matched.candidate["_id"],
            "confidence": min(12, matched.candidate["_score"]) / 12,
            "score": matched.candidate["_score"]
        }
    ]


def match_organizations(params, version):
    print("new_matching.py")
    if "affiliation" in params:
        active_only = True
        if "all_status" in params:
            if params["all_status"] == "" or params["all_status"].lower() == "true":
                active_only = False
        matched = match(params.get("affiliation"), active_only)
        print(matched)
        return None, MatchingResultV2(matched)
    return Errors('"affiliation" parameter missing'), None
