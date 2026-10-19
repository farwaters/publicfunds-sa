"""HTTP fetching with bounded retries and exponential backoff.

Policy (AGENTS.md / design §10): we never work around access controls. 401/403/WAF challenges raise
SourceBlocked immediately and are logged as incidents, not retried with different identities.
"""
from __future__ import annotations

import random
import time
from typing import Callable

import httpx

USER_AGENT = "Thusa/0.1 public-interest research (github.com/farwaters/publicfunds-sa)"
RETRY_STATUS = {429, 500, 502, 503, 504}
BLOCK_STATUS = {401, 403, 451}


class FetchError(RuntimeError):
    """Source unavailable after retries (transient or server error)."""


class SourceBlocked(FetchError):
    """Source refused access (auth/WAF). Never retried or circumvented."""


class Fetcher:
    def __init__(
        self,
        timeout: float = 180.0,
        retries: int = 4,
        backoff: float = 2.0,
        sleep: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.retries = retries
        self.backoff = backoff
        self.sleep = sleep
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            transport=transport,
        )
        self.requests_made = 0

    def _delay(self, attempt: int, retry_after: str | None) -> float:
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), 120.0)
        return self.backoff * (2**attempt) + random.uniform(0, self.backoff / 2)

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        last_err: str = ""
        for attempt in range(self.retries + 1):
            self.requests_made += 1
            try:
                resp = self.client.get(url, params=params)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                retry_after = None
            else:
                if resp.status_code in BLOCK_STATUS:
                    raise SourceBlocked(f"HTTP {resp.status_code} from {url}")
                if resp.status_code < 400:
                    return resp
                if resp.status_code not in RETRY_STATUS:
                    raise FetchError(f"HTTP {resp.status_code} from {url}")
                last_err = f"HTTP {resp.status_code}"
                retry_after = resp.headers.get("Retry-After")
            if attempt < self.retries:
                self.sleep(self._delay(attempt, retry_after))
        raise FetchError(f"{url} failed after {self.retries + 1} attempts: {last_err}")

    def close(self) -> None:
        self.client.close()
