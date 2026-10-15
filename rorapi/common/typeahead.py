import unicodedata
from itertools import groupby

from elasticsearch_dsl import Q

INNER_HITS_NAME = "matched_name"

_ID = "names_ids.id"
_EXACT = "names_ids.name.exact"
_EDGE = "names_ids.name.edge"
_CHAR_SEARCH = "typeahead_char_search"
_FUZZY_SEARCH = "typeahead_fuzzy_search"
# The mapping gives .edge string_lowercase as its search analyzer, so query.advanced's `*` expansion
# normalizes a fuzzy term as names_ids.name does instead of spelling Hangul syllables as jamo
# keystrokes until Lucene fails the request. Every .edge clause here names its typeahead analyzer.
_EDGE_SEARCH = "typeahead_edge_search"
_TYPES = "names_ids.types"

_MAX_MISSING_WORDS = 4

# No edit under 3 code points, so a one- or two-letter keystroke matches only names that start with it.
# Two edits on a long non-Latin whole name exceed Lucene's 10,000-state automaton and fail the request,
# so the second edit starts at 1,000 code points, past any term the analyzers emit.
_ONE_EDIT = "AUTO:3,1000"

# One edit also exceeds the 10,000-state limit for a whole name in a 3- or 4-byte script from about
# 740 UTF-8 bytes. Bytes, not code points, decide the failure, so the whole-name typo tier skips an
# input above 500 bytes.
_MAX_FUZZY_NAME_BYTES = 500

# Each fuzzy token walks the edge-gram term dictionary, so the word typo tiers cap the token count.
# _paired_token_count mirrors the engine's count, and the limit in typeahead_fuzzy_search is the hard
# bound. The tiers skip a longer input instead of fuzzing its first tokens, which would tie a long
# name with every sibling that shares them.
_MAX_FUZZY_TOKENS = 8

# A fuzzy match keeps the 50 closest terms by default and breaks ties by byte order, which can drop the
# intended word of a short token with many one-edit neighbours. 1,000 stays just under Lucene's 1,024
# clause limit.
_WORD_TYPO_EXPANSIONS = 1000

# A name's score packs its tier above its rank, and an identifier entry, which has no rank, scores
# below every name in its tier. So the nested max is the best tier and, within it, the lowest rank,
# and the inner hit's default _score order picks that same name. The sort pulls the tier back out so
# the prior sorts between the tier and the rank.
_TIER_SCALE = 1000
_RANKED_SCORE = (
    "_score * {0} + {1} - (doc['names_ids.rank'].size() == 0 ? {1} : doc['names_ids.rank'].value)"
).format(_TIER_SCALE, _TIER_SCALE - 1)
TIER_SORT = {"_script": {
    "type": "number",
    "order": "desc",
    "script": {"source": "Math.floor(_score / {})".format(_TIER_SCALE)},
}}

_KIND_RANK = {"ror_display": 0, "label": 0, "alias": 1, "acronym": 2}
_FULL_NAME_TYPES = ["ror_display", "label", "alias"]

_TOKEN_STEP = 2
_MAX_RANKED_TOKENS = 99
_KIND_BAND = _TOKEN_STEP * (_MAX_RANKED_TOKENS + 1)

# The word analyzers keep an apostrophe in any of these spellings, and U+200C, inside the token
# (typeahead_joiners_to_apostrophe), so Hawai'i is one word in Python and in the engine. The analyzers
# delete every other format character except U+200B (typeahead_drop_format), so Python keeps those
# inside the word. U+200B becomes a space (typeahead_non_alnum_to_space).
_JOINERS = frozenset("'\u2018\u2019\u0060\u00b4\u200c")


def _is_mark_or_format(ch):
    category = unicodedata.category(ch)
    return category[0] == "M" or (category == "Cf" and ch != "\u200b" and ch not in _JOINERS)


def _is_word_char(ch):
    return unicodedata.category(ch)[0] in "LN" or ch in _JOINERS or _is_mark_or_format(ch)


def _word_spans(text):
    spans, pos = [], 0
    for is_word, chars in groupby(text, _is_word_char):
        run = "".join(chars)
        if is_word and any(unicodedata.category(c)[0] in "LN" for c in run):
            spans.append((pos, pos + len(run)))
        pos += len(run)
    return spans


def _words(text):
    return [text[start:end] for start, end in _word_spans(text)]


def _token_class(ch):
    category = unicodedata.category(ch)
    if category[0] == "M" or category == "Cf" or ch in _JOINERS:
        return None
    name = unicodedata.name(ch, "")
    if "IDEOGRAPH" in name or name.startswith("HIRAGANA"):
        return "ideograph"
    return "katakana" if "KATAKANA" in name else "other"


def _token_count(text):
    # Mirrors the standard tokenizer: each Han or Hiragana character is a token by itself, a Katakana
    # run is one token, and so is a run of any other letters and digits. A mark stays with its character.
    count = 0
    for start, end in _word_spans(text):
        last = None
        for ch in text[start:end]:
            token_class = _token_class(ch)
            if last and (token_class is None or (token_class == last and token_class != "ideograph")):
                continue
            count += 1
            last = token_class or "other"
    return count


def _paired_token_count(text):
    # typeahead_fuzzy_search counts tokens after cjk_bigram, which turns each run of n >= 2 Han or
    # Hiragana characters into n - 1 pairs. A mark or a format character other than U+200B does not
    # end a run. A joiner (_JOINERS) does, and so do 々 and 〻, which the tokenizer emits as letters.
    pairable = [_token_class(c) == "ideograph" and c not in "々〻"
                for c in text if not _is_mark_or_format(c)]
    pairs = sum(1 for is_pairable, run in groupby(pairable) if is_pairable and len(list(run)) > 1)
    return _token_count(text) - pairs


def _fold(word):
    decomposed = unicodedata.normalize("NFKD", word)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


OPTIONAL_WORDS = frozenset(_fold(w) for w in (
    "the", "of", "and", "for", "at", "in", "on", "de", "del", "della", "di", "du", "des", "la", "le", "les", "el",
    "los", "las", "da", "do", "dos", "das", "der", "die", "und", "für", "y", "e", "et", "a", "an", "en",
    "co", "ltd", "inc", "llc", "gmbh", "sa", "ag", "plc", "srl", "bv", "nv", "kk", "spa", "sas", "corp", "pvt", "pty",
))


def clean(raw):
    return unicodedata.normalize("NFC", raw).strip()


def name_rank(name):
    kind = min(_KIND_RANK[t] for t in name["types"])
    # The index puts each apostrophe part at its own position (typeahead_apostrophe_parts), so the
    # count reads the apostrophe set and U+200C as spaces. Other format characters stay joined.
    value = "".join(" " if c in _JOINERS else c for c in name["value"])
    length = _token_count(value)
    # A translated label often has as many words as the display name; the odd step makes the display
    # name the matched name on that tie.
    return (_KIND_BAND * kind + _TOKEN_STEP * min(length, _MAX_RANKED_TOKENS)
            + ("ror_display" not in name["types"]))


def validation_errors(raw):
    if not _words(clean(raw)):
        return ["query.typeahead must contain at least one letter or digit"]
    return []


def _required(words):
    return [w for w in words if _fold(w) not in OPTIONAL_WORDS] or words


def required_words(text):
    return " ".join(_required(_words(text)))


def typed_words(text):
    spans = _word_spans(text)
    words = [text[start:end] for start, end in spans]
    required = _required(words)
    last_dropped = required[-1:] != words[-1:]
    last_may_be_partial = bool(spans) and spans[-1][1] == len(text)
    return " ".join(required + words[-1:] if last_dropped and last_may_be_partial else required)


def _ordered(words):
    # ES 7.10's empty intervals source fails inside a conjunction. The match clause turns zero
    # tokens into no match before the intervals clause runs.
    analyzed = {"query": words, "analyzer": _CHAR_SEARCH}
    return Q("bool", filter=[
        Q("match", **{_EDGE: dict(analyzed, operator="and")}),
        Q("intervals", **{_EDGE: {"match": dict(analyzed, ordered=True, max_gaps=-1)}}),
    ])


def tiers(text):
    required = required_words(text)
    # A term or prefix query would normalize unsearchable text to "", and "" prefixes every name.
    exact = Q("match", **{_EXACT: text})
    acronym = Q("term", **{_TYPES: "acronym"})
    full_name = Q("terms", **{_TYPES: _FULL_NAME_TYPES})
    name_within_one_edit = Q("match", **{_EXACT: {"query": text, "fuzziness": _ONE_EDIT}})
    # One edit on an acronym's few letters reaches dozens of other acronyms, and at this tier every one
    # of them would rank above the word the user misspelled, so the whole-name typo tier skips names
    # whose only type is acronym.
    name_typo = [
        (58, Q("bool", filter=[name_within_one_edit, full_name])),
    ] if len(text.encode()) <= _MAX_FUZZY_NAME_BYTES else []
    typo_words = {
        "query": required, "analyzer": _FUZZY_SEARCH, "operator": "and",
        "max_expansions": _WORD_TYPO_EXPANSIONS,
    }
    word_typo = [
        (56, Q("match", **{_EDGE: dict(typo_words, fuzziness=_ONE_EDIT)})),
        (55, Q("match", **{_EDGE: dict(typo_words, fuzziness="AUTO", prefix_length=1)})),
    ] if _paired_token_count(required) <= _MAX_FUZZY_TOKENS else []
    return [
        (100, Q("bool", should=[
            Q("bool", filter=[exact, full_name]),
            Q("term", **{_ID: text}),
        ])),
        (90, Q("bool", filter=[exact, acronym])),
        (80, Q("match_bool_prefix", **{_EXACT: text})),
        (75, _ordered(typed_words(text))),
        (70, _ordered(required)),
        (60, Q("match", **{_EDGE: {"query": required, "analyzer": _EDGE_SEARCH, "operator": "and"}})),
    ] + name_typo + word_typo + [
        (50, Q("match", **{_EDGE: {
            "query": required, "analyzer": _EDGE_SEARCH, "minimum_should_match": "2<-1"}})),
    ] + [
        (43 - i, Q("match", **{_EDGE: {
            "query": required, "analyzer": _EDGE_SEARCH,
            "minimum_should_match": "{}<-{}".format(2 * missing - 1, missing)}}))
        for i, missing in enumerate(range(2, _MAX_MISSING_WORDS + 1))
    ]


def text_query(text):
    return _nested_query(tiers(text))


def id_query(ror_id):
    # A ROR ID lookup skips the default status filter, so a name tier here would surface inactive and
    # withdrawn records by name.
    return _nested_query([(100, Q("term", **{_ID: ror_id}))])


def _nested_query(scored_tiers):
    any_tier = Q("dis_max", queries=[
        Q("constant_score", filter=f, boost=boost) for boost, f in scored_tiers
    ])
    ranked = Q(
        "function_score",
        query=any_tier,
        script_score={"script": {"source": _RANKED_SCORE}},
        boost_mode="replace",
    )
    return Q(
        "nested",
        path="names_ids",
        score_mode="max",
        query=ranked,
        inner_hits={"name": INNER_HITS_NAME, "size": 1, "_source": False},
    )
