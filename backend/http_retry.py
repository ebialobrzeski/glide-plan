"""Shared HTTP retry helper for outbound calls to external APIs.

Public APIs such as Overpass (OpenStreetMap), OpenAIP and the elevation
services occasionally return rate-limit (429) or transient gateway/overload
errors (502/503/504). This module centralises the retry behaviour:

  * the server's ``Retry-After`` header is honoured when present (both the
    delta-seconds and HTTP-date forms allowed by RFC 7231);
  * otherwise an exponential backoff (1s, 2s, 4s …) is used;
  * every wait is capped so a single web request can't block for too long.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

logger = logging.getLogger(__name__)

# HTTP responses worth retrying: rate limiting (429) and transient gateway /
# overload errors (502/503/504) that public servers return when busy.
RETRY_STATUSES = frozenset({429, 502, 503, 504})
DEFAULT_MAX_RETRIES = 2          # extra attempts after the first try
DEFAULT_MAX_WAIT_S = 10.0        # cap each wait so a request can't hang for long


def parse_retry_after(value: str | None) -> float | None:
    """Parse an HTTP ``Retry-After`` header into seconds to wait.

    Supports both forms allowed by RFC 7231: an integer number of seconds, or
    an HTTP-date. Returns ``None`` when the header is absent or unparseable.
    """
    if not value:
        return None
    value = value.strip()
    # delta-seconds form, e.g. "120"
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    # HTTP-date form, e.g. "Wed, 21 Oct 2025 07:28:00 GMT"
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0.0, (dt - datetime.now(timezone.utc)).total_seconds())


def request_with_retry(
    method: str,
    url: str,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    max_wait_s: float = DEFAULT_MAX_WAIT_S,
    **kwargs,
) -> requests.Response:
    """Issue an HTTP request, retrying on rate-limit / transient gateway errors.

    The server's ``Retry-After`` header is honoured when present; otherwise an
    exponential backoff (1s, 2s, 4s …) is used. Each wait is capped at
    ``max_wait_s`` so a single web request can't block for too long.

    The final :class:`requests.Response` is returned (even if it still carries a
    retryable status) so the caller can ``raise_for_status()`` and surface a
    meaningful error. Network-level exceptions are re-raised after the last try.
    """
    last_response: requests.Response | None = None
    last_exc: requests.RequestException | None = None

    for attempt in range(max_retries + 1):
        last_response = None
        try:
            resp = requests.request(method, url, **kwargs)
        except requests.RequestException as exc:
            last_exc = exc
        else:
            last_exc = None
            last_response = resp
            if resp.status_code not in RETRY_STATUSES:
                return resp

        if attempt >= max_retries:
            break

        wait = parse_retry_after(last_response.headers.get('Retry-After')) if last_response is not None else None
        if wait is None:
            wait = 2.0 ** attempt
        wait = min(wait, max_wait_s)

        reason = f'HTTP {last_response.status_code}' if last_response is not None else f'error: {last_exc}'
        logger.info(
            'Retrying %s %s in %.1fs (attempt %d/%d) — %s',
            method, url, wait, attempt + 1, max_retries, reason,
        )
        time.sleep(wait)

    if last_response is not None:
        return last_response  # caller's raise_for_status() surfaces the final error
    raise last_exc  # only network exceptions occurred
