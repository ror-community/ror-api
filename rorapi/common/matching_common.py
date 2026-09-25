import os
import re
import unicodedata
import unidecode

from functools import lru_cache
from rapidfuzz import fuzz


@lru_cache(maxsize=None)
def _load_countries():
    """Load custom country code map from countries.txt"""

    countries = []
    with open(os.path.join(os.path.split(__file__)[0], "countries.txt")) as file:
        lines = [line.strip().split() for line in file]
        countries = [(line[0], " ".join(line[1:])) for line in lines]
    return countries


_COUNTRIES = _load_countries()


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
    for code, name in _COUNTRIES:
        if re.search("[^a-z]", name):
            score = fuzz.partial_ratio(name, lower)
        elif len(name) == 2:
            score = max([fuzz.ratio(name.upper(), t) for t in alpha.split()] + [0])
        else:
            score = max([fuzz.ratio(name, t) for t in lower_alpha.split()] + [0])
        if score >= 90:
            codes.append(code.upper())
    return list(set(codes))


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
        "(?<![a-z])lab$", "laboratory", re.sub("(?<![a-z])lab[^a-z]", "laboratory ", s)
    )
    s = re.sub(
        "(?<![a-z])inst$", "institute", re.sub("(?<![a-z])inst[^a-z]", "institute ", s)
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
