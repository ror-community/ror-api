import re
import requests

from statsmodels.stats.api import DescrStatsW, proportion_confint


def escape_query(query):
    return re.sub(r'([\+\-=\&\|><!\(\)\{\}\[\]\^"\~\*\?:\\\/])',
                  lambda m: '\\' + m.group(), query)


def search(url, param, query, escape=True):
    if escape:
        query = escape_query(query)
    results = requests.get('{}/organizations'.format(url),
                           {param: query}).json()
    if 'items' not in results:
        return []
    return results['items']


def get_rank(ror_id, items):
    for i, item in enumerate(items):
        if ror_id == item['id']:
            return i+1
    return 21


def mean_rank(ranks):
    return sum(ranks) / len(ranks), DescrStatsW(ranks).tconfint_mean()


def recall_at_n(ranks, n):
    s = len([r for r in ranks if r <= n])
    a = len(ranks)
    return s / a, proportion_confint(s, a)
