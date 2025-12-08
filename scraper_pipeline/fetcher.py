# scraper_pipeline/fetcher.py

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import requests
from requests import Response

logger = logging.getLogger(__name__)


@dataclass
class FetchedPage:
    """
    Result of fetching a single URL.

    This is intentionally separate from the Document object. It represents
    the raw HTTP-level result (status code, HTML text) before parsing.
    """

    url: str                  # URL we attempted to fetch (after redirects)
    status_code: int          # HTTP status code (e.g., 200, 404, 503)
    text: Optional[str]       # Response body as text (HTML), or None on failure
    final_url: Optional[str]  # Final URL after redirects, if any
    error: Optional[str]      # Error message if something went wrong


class FetchError(Exception):
    """Custom exception raised when fetching fails in a non-recoverable way"""
    pass


class Fetcher:
    """
    Simple HTTP fetcher using the `requests` library

    Responsibilities:
    - Attach a custom User-Agent header (good practice for crawlers)
    - Apply timeouts to avoid hanging
    - Retry on transient errors with exponential backoff
    - Return a FetchedPage object describing the outcome
    """

    def __init__(
        self,
        user_agent: str = "ResearchProjectCrawler (https://github.com/pranitahuja00/Web-Scraping-Pipeline-LLM-RAG)",
        timeout_seconds: int = 10,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
    ) -> None:
        """
        param user_agent: String to send in the User-Agent header
        param timeout_seconds: Per-request timeout to avoid hanging forever
        param max_retries: How many times to retry on transient errors
        param backoff_factor: Sleep time grows like backoff_factor * (2 ** attempt)
        """
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        # Use a Session for connection pooling and efficiency.
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    def _should_retry(self, status_code: int) -> bool:
        """
        Decide whether to retry based on HTTP status code
        """
        if status_code >= 500:
            return True
        if status_code == 429:
            return True
        return False

    def fetch(self, url: str) -> FetchedPage:
        """
        Fetch a single URL and return a FetchedPage.

        This method NEVER raises for common HTTP errors; it only raises FetchError
        if something fundamentally unexpected happens. The crawler can then decide
        how to handle failures by inspecting FetchedPage.error.
        """
        attempt = 0
        last_exception: Optional[Exception] = None

        while attempt <= self.max_retries:
            try:
                logger.debug("Fetching URL %s (attempt %d)", url, attempt + 1)
                resp: Response = self.session.get(
                    url,
                    timeout=self.timeout_seconds,
                    allow_redirects=True,
                )

                # If success-ish (200-399), return immediately.
                if 200 <= resp.status_code < 400:
                    logger.info("Fetched %s with status %d", url, resp.status_code)
                    return FetchedPage(
                        url=url,
                        status_code=resp.status_code,
                        text=resp.text,
                        final_url=str(resp.url),
                        error=None,
                    )

                # Non-success status codes
                logger.warning(
                    "Non-success status %d for URL %s", resp.status_code, url
                )

                if self._should_retry(resp.status_code) and attempt < self.max_retries:
                    sleep_seconds = self.backoff_factor * (2 ** attempt)
                    logger.info(
                        "Retrying %s after %s seconds due to status %d",
                        url,
                        sleep_seconds,
                        resp.status_code,
                    )
                    time.sleep(sleep_seconds)
                    attempt += 1
                    continue

                # If we shouldn't retry, return a FetchedPage with error info.
                return FetchedPage(
                    url=url,
                    status_code=resp.status_code,
                    text=None,
                    final_url=str(resp.url),
                    error=f"HTTP {resp.status_code}",
                )

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                # Transient network issue; optionally retry.
                last_exception = e
                logger.warning("Network error for %s: %s", url, e)

                if attempt < self.max_retries:
                    sleep_seconds = self.backoff_factor * (2 ** attempt)
                    logger.info(
                        "Retrying %s after %s seconds due to network error",
                        url,
                        sleep_seconds,
                    )
                    time.sleep(sleep_seconds)
                    attempt += 1
                    continue

                # Out of retries, give up.
                return FetchedPage(
                    url=url,
                    status_code=0,
                    text=None,
                    final_url=None,
                    error=str(e),
                )

            except Exception as e:
                # Something unexpected happened; you might choose to re-raise.
                logger.error("Unexpected error fetching %s: %s", url, e, exc_info=True)
                raise FetchError(f"Unexpected error fetching {url}: {e}") from e

        # Defensive, should not reach here.
        raise FetchError(
            f"Failed to fetch {url} after {self.max_retries} retries (last_exception={last_exception})"
        )
