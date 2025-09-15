import os
import re
import unicodedata
import unidecode

from rorapi.common.models import Errors
from rorapi.settings import ES7
from rorapi.common.es_utils import ESQueryBuilder
from rorapi.v1.models import MatchingResult as MatchingResultV1
from rorapi.v2.models import MatchingResult as MatchingResultV2

from collections import namedtuple
from functools import lru_cache
from rapidfuzz import fuzz
from itertools import groupby

MIN_SCORE = 96
MIN_SCORE_FOR_RETURN = 50

MATCHING_TYPE_SINGLE = "SINGLE SEARCH"

# Matching strategy from Marple:
# https://gitlab.com/crossref/labs/marple/-/blob/main/strategies_available/affiliation_single_search/strategy.py?ref_type=heads

@lru_cache(maxsize=None)
def load_countries():
    """Load custom country code map from countries.txt. Tried to use geonames but it gave worse results since it only 
    includes country names. Might be worth it to try again in the future."""
    countries = []
    with open(os.path.join(os.path.split(__file__)[0], "countries.txt")) as file:
        lines = [line.strip().split() for line in file]
        countries = [(line[0], " ".join(line[1:])) for line in lines]
    return countries


GEONAMES_COUNTRIES = load_countries()


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
    return [c._replace(rescore=ns) for c, ns in zip(candidates, new_scores)]


def score(aff, candidate):
    best = MatchedOrganization(
        organization=candidate,
        name="",
        score=0,
        rescore=0,
        start=-1,
        end=-1,
        matching_type=MATCHING_TYPE_SINGLE,
        substring=aff,
        chosen=False,
    )
    for candidate_name in candidate["_source"]["affiliation_match"]["names"]:
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
            alignment = fuzz.partial_ratio_alignment(normalize(aff), normalize(name))
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
                    chosen=False,
                )
    return best

def choose_candidate(rescored):

    top_score = max([c.rescore for c in rescored])
    top_scored = [c for c in rescored if c.rescore == top_score]

    if len(top_scored) == 1:
        return top_scored[0]
    
    return last_non_overlapping(top_scored)

MatchedOrganization = namedtuple(
    "MatchedOrganization",
    [
        "organization",
        "name",
        "score",
        "rescore",
        "start",
        "end",
        "matching_type",
        "substring",
        "chosen",
    ],
)
MatchedOrganization.__new__.__defaults__ = (None, None, 0, 0, 0, 0, None, None, False)

def match_by_query(text, query, countries):
    """Match affiliation text using specific ES query."""
    try:
        scored_candidates = []
        chosen_candidate = None
        chosen_true = None
        results = query.execute()
    except Exception as e:
        return f"query error: {e}", None
    try:
        candidates = results.hits.hits
    except Exception as e:
        return f"candidates error: {e}\n{results}", None
    if candidates:
        candidates = [c for c in candidates if c["_source"]["status"] == "active"]
        scored_candidates = [score(text, c) for c in candidates]
        scored_candidates = [s for s in scored_candidates if s.score >= MIN_SCORE_FOR_RETURN]
        if scored_candidates:
            if (len(scored_candidates) == 1) and (scored_candidates[0].score >= MIN_SCORE):
                chosen_candidate = scored_candidates[0]
            if len(scored_candidates) > 1:
                rescored_candidates = rescore(text, scored_candidates)
                rescored_candidates = [
                    r for r in rescored_candidates if r.score >= MIN_SCORE
                ]
                if rescored_candidates:
                    chosen_candidate = choose_candidate(rescored_candidates)
            if chosen_candidate:
                if (countries
                    and to_region(chosen_candidate[0]["_source"]["locations"][0]["geonames_details"]["country_code"]) 
                    not in countries):
                    pass
                else:
                    chosen_true = MatchedOrganization(
                        organization=chosen_candidate.organization,
                        name=chosen_candidate.name,
                        rescore=chosen_candidate.rescore,
                        score=round(chosen_candidate.score / 100, 2),
                        start=chosen_candidate.start,
                        end=chosen_candidate.end,
                        matching_type=MATCHING_TYPE_SINGLE,
                        substring=chosen_candidate.substring,
                        chosen=True,
                    )
        scored_candidates = [
            s._replace(score=round(s.score / 100, 2)) for s in scored_candidates
        ]

    return chosen_true, scored_candidates


def get_output(chosen, all_matched, active_only):
    if active_only:
        all_matched = [
            m for m in all_matched if m.organization["_source"]["status"] == "active"
        ]
    all_matched = sorted(all_matched, key=lambda x: x.score, reverse=True)[:100]
    if chosen:
        all_matched = [
            a
            for a in all_matched
            if a.organization["_id"] != chosen.organization["_id"]
        ]
        all_matched.insert(0, chosen)
    return all_matched


def get_candidates(aff, countries, version):
    qb = ESQueryBuilder(version)
    try:
        qb.add_affiliation_query(aff, 200)
        return match_by_query(aff, qb.get_query(), countries)
    except Exception as e:
        try:
            # get index info like the mappings
            curr_v2_index = ES7.get('organizations-v2')['mappings']
            return curr_v2_index, None
        except Exception as e2:
            return f"query error: {e2}", None
        return f"query error: {e2}", None


def match_affiliation(affiliation, active_only, version):
    countries = get_countries(affiliation)
    chosen, all_matched = get_candidates(affiliation, countries, version)
    if isinstance(chosen, str):
        return chosen
    return get_output(chosen, all_matched, active_only)


def match_organizations(params, version):
    if "affiliation" in params:
        active_only = True
        if "all_status" in params:
            if params["all_status"] == "" or params["all_status"].lower() == "true":
                active_only = False
        matched = match_affiliation(params.get("affiliation"), active_only, version)

        if isinstance(matched, str):
            return Errors(["{}".format(matched)]), None
        
        if version == "v2":
            return None, MatchingResultV2(matched)
        return None, MatchingResultV1(matched)
    return Errors(["'affiliation' parameter missing"]), None