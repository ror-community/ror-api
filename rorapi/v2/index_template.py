import json
import unicodedata
from itertools import product

from rorapi.settings import ES_VARS

HANGUL_SYLLABLES = range(0xAC00, 0xD7A4)
# Unicode orders the syllable block by initial, then medial, then final, as these
# tables are ordered.
HANGUL_INITIALS = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'
HANGUL_MEDIALS = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ'
HANGUL_FINALS = ['', *'ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ']
TWO_KEY_JAMO = {
    'ㅘ': 'ㅗㅏ', 'ㅙ': 'ㅗㅐ', 'ㅚ': 'ㅗㅣ', 'ㅝ': 'ㅜㅓ',
    'ㅞ': 'ㅜㅔ', 'ㅟ': 'ㅜㅣ', 'ㅢ': 'ㅡㅣ',
    'ㄳ': 'ㄱㅅ', 'ㄵ': 'ㄴㅈ', 'ㄶ': 'ㄴㅎ', 'ㄺ': 'ㄹㄱ', 'ㄻ': 'ㄹㅁ', 'ㄼ': 'ㄹㅂ',
    'ㄽ': 'ㄹㅅ', 'ㄾ': 'ㄹㅌ', 'ㄿ': 'ㄹㅍ', 'ㅀ': 'ㄹㅎ', 'ㅄ': 'ㅂㅅ',
    'ㄲ': 'ㄱㄱ', 'ㄸ': 'ㄷㄷ', 'ㅃ': 'ㅂㅂ', 'ㅆ': 'ㅅㅅ', 'ㅉ': 'ㅈㅈ',
}


def nfc_rules():
    """A mapping char filter replaces literal strings, so each decomposed spelling that
    NFC composes to one code point needs a rule of its own."""
    rules = {}
    for cp in range(0x110000):
        if cp in HANGUL_SYLLABLES:
            continue
        char = chr(cp)
        nfc = unicodedata.normalize('NFC', char)
        if nfc != char:
            rules[char] = nfc
            continue
        text = char
        while True:
            decomposition = unicodedata.decomposition(text[0])
            if not decomposition or decomposition.startswith('<'):
                break
            text = ''.join(chr(int(h, 16)) for h in decomposition.split()) + text[1:]
            if unicodedata.normalize('NFC', text) == char:
                rules[text] = char
    return [f'{source} => {target}' for source, target in sorted(rules.items())]


def two_set_keys(jamo):
    return ''.join(TWO_KEY_JAMO.get(j, j) for j in jamo)


def hangul_key_rules():
    jamo = product(HANGUL_INITIALS, HANGUL_MEDIALS, HANGUL_FINALS)
    syllables = zip(map(chr, HANGUL_SYLLABLES), jamo, strict=True)
    rules = [f'{syllable} => {two_set_keys(parts)}' for syllable, parts in syllables]
    return rules + [f'{j} => {two_set_keys(j)}' for j in sorted(TWO_KEY_JAMO)]


def index_template():
    with open(ES_VARS['INDEX_TEMPLATE_ES7_V2'], encoding='utf-8') as f:
        template = json.load(f)
    char_filters = template['settings']['analysis']['char_filter']
    char_filters['typeahead_nfc']['mappings'] = nfc_rules()
    char_filters['typeahead_hangul_keys']['mappings'] = hangul_key_rules()
    return template
