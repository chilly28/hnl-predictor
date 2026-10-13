"""Small, polite HTTP helper shared by all data sources."""

from __future__ import annotations

import json
import logging
import time

import requests

log = logging.getLogger(__name__)

USER_AGENT = "hnl-predictor/1.0 (+https://github.com/chilly28/hnl-predictor; non-commercial analytics)"
_last_call: dict[str, float] = {}


def _throttle(host: str, min_interval: float) -> None:
    wait = _last_call.get(host, 0) + min_interval - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def fetch_text(url: str, *, headers: dict | None = None, params: dict | None = None,
               timeout: float = 20, min_interval: float = 1.0, retries: int = 2,
               quiet_404: bool = False) -> str | None:
    """GET a URL and return text, or None on failure. Never raises."""
    host = url.split("/")[2]
    hdrs = {"User-Agent": USER_AGENT}
    hdrs.update(headers or {})
    for attempt in range(retries + 1):
        _throttle(host, min_interval)
        try:
            r = requests.get(url, headers=hdrs, params=params, timeout=timeout)
        except requests.RequestException as exc:
            log.warning("GET %s failed: %s", url, exc)
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            return None
        if r.status_code == 404:
            if not quiet_404:
                log.warning("GET %s -> 404", url)
            return None
        if r.status_code == 429 or r.status_code >= 500:
            log.warning("GET %s -> %s (attempt %d)", url, r.status_code, attempt + 1)
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code != 200:
            log.warning("GET %s -> %s", url, r.status_code)
            return None
        r.encoding = r.encoding or "utf-8"
        return r.text
    return None


def fetch_json(url: str, **kwargs):
    text = fetch_text(url, **kwargs)
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        log.warning("GET %s returned invalid JSON", url)
        return None
