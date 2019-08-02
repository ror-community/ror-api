import re
import requests


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
