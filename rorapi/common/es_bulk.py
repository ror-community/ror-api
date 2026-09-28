"""Retry wrapper for Elasticsearch/OpenSearch bulk indexing."""

import logging
import random
import time

from elasticsearch import ConnectionError as ESConnectionError
from elasticsearch import ConnectionTimeout, TransportError

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = frozenset({429, 502, 503, 504})
DEFAULT_MAX_ATTEMPTS = 6
DEFAULT_BASE_DELAY = 1.0
DEFAULT_MAX_DELAY = 30.0


def is_retryable(exc):
    """Return True if the exception is a transient ES/OpenSearch failure."""
    if isinstance(exc, (ESConnectionError, ConnectionTimeout)):
        return True
    if isinstance(exc, TransportError):
        status = getattr(exc, 'status_code', None)
        try:
            return int(status) in RETRYABLE_STATUS_CODES
        except (TypeError, ValueError):
            return False
    return False


def bulk_with_retry(
        es_client,
        body,
        max_attempts=DEFAULT_MAX_ATTEMPTS,
        base_delay=DEFAULT_BASE_DELAY,
        max_delay=DEFAULT_MAX_DELAY):
    """Call ``es_client.bulk(body)`` with exponential backoff on transient errors.

    Retries HTTP 429/502/503/504 and connection/timeout errors. After
    ``max_attempts`` failures, re-raises the last ``TransportError``.
    """
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return es_client.bulk(body)
        except TransportError as exc:
            last_exc = exc
            if not is_retryable(exc) or attempt >= max_attempts:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            delay = delay * (0.5 + random.random())
            status = getattr(exc, 'status_code', 'unknown')
            logger.warning(
                'Transient Elasticsearch bulk error (status=%s), '
                'attempt %s/%s, retrying in %.2fs: %s',
                status, attempt, max_attempts, delay, exc)
            time.sleep(delay)
    raise last_exc
