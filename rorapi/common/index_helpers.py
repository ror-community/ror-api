"""Shared helpers for ROR Elasticsearch indexing commands.

Used by ``indexror`` and ``indexrordump``. Bulk calls go through
``_bulk``, which uses ``bulk_with_retry`` so transient Elasticsearch
errors back off without duplicating the chunk loop.
"""

import re

from elasticsearch import TransportError

from rorapi.common.es_bulk import bulk_with_retry
from rorapi.settings import ES7, ES_VARS


def get_nested_names_v2(org):
    for name in org['names']:
        yield name['value']


def get_nested_ids_v2(org):
    yield org['id']
    yield re.sub('https://', '', org['id'])
    yield re.sub('https://ror.org/', '', org['id'])
    for ext_id in org['external_ids']:
        for eid in ext_id['all']:
            yield eid


def get_single_search_names_v2(org):
    for name in org["names"]:
        if "acronym" not in name["types"]:
            yield name["value"]


def get_affiliation_match_doc(org):
    return {
        'id': org['id'],
        'country': org["locations"][0]["geonames_details"]["country_code"],
        'status': org['status'],
        'primary': [n["value"] for n in org["names"] if "ror_display" in n["types"]][0],
        'names': [{"name": n} for n in get_single_search_names_v2(org)],
        'relationships': [{"type": r['type'], "id": r['id']} for r in org['relationships']]
    }


def enrich_org_for_index(org):
    """Attach ``names_ids`` and ``affiliation_match`` fields used by the index."""
    org['names_ids'] = [{
        'name': n
    } for n in get_nested_names_v2(org)]
    org['names_ids'] += [{
        'id': n
    } for n in get_nested_ids_v2(org)]
    org['affiliation_match'] = get_affiliation_match_doc(org)
    return org


def build_bulk_body(index, orgs):
    """Build an ES bulk body for a chunk of organizations."""
    body = []
    for org in orgs:
        body.append({
            'index': {
                '_index': index,
                '_id': org['id']
            }
        })
        enrich_org_for_index(org)
        body.append(org)
    return body


def _bulk(body):
    """Perform one bulk request, retrying transient Elasticsearch errors."""
    return bulk_with_retry(ES7, body)


def maybe_backup_index(index, backup_index):
    """Create a backup unless one already exists or the live index is empty.

    When ``setup`` has already written ``backup_index``, leave it alone so a
    failed bulk load can restore the previous live data rather than an empty
    new index.
    """
    if ES7.indices.exists(backup_index):
        return
    if not ES7.indices.exists(index):
        return
    count = ES7.count(index=index).get('count', 0)
    if count == 0:
        return
    ES7.reindex(body={
        'source': {
            'index': index
        },
        'dest': {
            'index': backup_index
        }
    })


def bulk_index_with_backup(index, dataset, on_transport_error=None, bulk=None):
    """Backup ``index`` to ``{index}-tmp``, bulk-index ``dataset``, restore on failure.

    Returns ``True`` if bulk indexing completed without ``TransportError``,
    ``False`` if a transport error triggered rollback. Does not re-raise;
    callers that must surface the failure should do so from
    ``on_transport_error``'s stored exception after this returns. Deletes the
    backup index when it exists.
    """
    if bulk is None:
        bulk = _bulk
    backup_index = '{}-tmp'.format(index)
    maybe_backup_index(index, backup_index)

    try:
        for i in range(0, len(dataset), ES_VARS['BULK_SIZE']):
            chunk = dataset[i:i + ES_VARS['BULK_SIZE']]
            body = build_bulk_body(index, chunk)
            bulk(body)
    except TransportError as e:
        if on_transport_error is not None:
            on_transport_error(e)
        if ES7.indices.exists(backup_index):
            ES7.reindex(body={
                'source': {
                    'index': backup_index
                },
                'dest': {
                    'index': index
                }
            })
            ES7.indices.delete(backup_index)
        return False
    if ES7.indices.exists(backup_index):
        ES7.indices.delete(backup_index)
    return True
