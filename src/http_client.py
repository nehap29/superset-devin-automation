"""Shared HTTP client with retry logic and request logging."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import Config

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_FACTOR = 1.0  # 1s, 2s, 4s
_RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
_DEFAULT_TIMEOUT = 30


def _build_session() -> requests.Session:
    """Create a requests.Session with automatic retries on transient errors."""
    session = requests.Session()
    retry = Retry(
        total=_MAX_RETRIES,
        backoff_factor=_BACKOFF_FACTOR,
        status_forcelist=_RETRY_STATUS_CODES,
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_session = _build_session()


def github_headers() -> dict[str, str]:
    return {
        "Authorization": f"token {Config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def devin_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {Config.DEVIN_API_KEY}",
        "Content-Type": "application/json",
    }


def get(
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> requests.Response:
    """HTTP GET with retries and structured logging."""
    start = time.monotonic()
    resp = _session.get(url, headers=headers, params=params, timeout=timeout)
    elapsed_ms = (time.monotonic() - start) * 1000
    logger.debug("GET %s — %d (%.0fms)", url, resp.status_code, elapsed_ms)
    resp.raise_for_status()
    return resp


def post(
    url: str,
    headers: dict[str, str],
    json_body: dict[str, Any] | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> requests.Response:
    """HTTP POST with retries and structured logging."""
    start = time.monotonic()
    resp = _session.post(url, headers=headers, json=json_body, timeout=timeout)
    elapsed_ms = (time.monotonic() - start) * 1000
    logger.debug("POST %s — %d (%.0fms)", url, resp.status_code, elapsed_ms)
    resp.raise_for_status()
    return resp
