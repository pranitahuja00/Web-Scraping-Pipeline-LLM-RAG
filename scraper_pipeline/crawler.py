# scraper_pipeline/crawler.py

from __future__ import annotations
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse, urlunparse, urldefrag
from bs4 import BeautifulSoup
from .fetcher import Fetcher, FetchedPage

logger = logging.getLogger(__name__)


@dataclass
class CrawlConfig:
    """
    Configuration for the Crawler.

    This determines what domain we stay on, how deep we go, how many pages we
    collect, and which path prefixes are considered relevant.
    """

    # Root domain restriction, e.g. "consumerfinance.gov"
    allowed_domain: str

    # Starting URLs (seeds) for the crawl
    start_urls: List[str]

    # Path prefixes (within the domain) that we consider "in scope"
    # e.g. ["/consumer-tools/credit-cards/answers/", "/ask-cfpb/"]
    allowed_path_prefixes: List[str]

    # How deep BFS should go from seed URLs
    max_depth: int = 3

    # Hard limit on number of pages to fetch successfully
    max_pages: int = 200

    # Delay between requests in seconds (basic politeness)
    delay_seconds: float = 0.5

    # Optional extra disallowed path prefixes (beyond robots.txt)
    # e.g. ["/ask-cfpb/search", "/askcfpb/search"]
    disallowed_path_prefixes: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.disallowed_path_prefixes is None:
            self.disallowed_path_prefixes = []


@dataclass
class CrawledPage:
    """
    Represents a successfully crawled HTML page with its crawl metadata.

    This is not yet our final Document schema, just a "raw HTML + URL + depth".
    The parser/cleaner will turn this into Document objects later.
    """

    url: str
    html: str
    depth: int
    parent_url: Optional[str]


class Crawler:
    """
    BFS-based crawler on top of a Fetcher.

    Responsibilities:
    - Start from one or more seed URLs.
    - Stay within the allowed domain and path prefixes.
    - Obey simple depth and page limits.
    - Extract internal links from each page and enqueue them.
    - Yield CrawledPage objects for further processing (parsing/cleaning).
    """

    def __init__(
        self,
        fetcher: Fetcher,
        config: CrawlConfig,
    ) -> None:
        self.fetcher = fetcher
        self.config = config

        # Track normalized URLs we've already seen (avoid loops and duplicates)
        self._seen_urls: Set[str] = set()

    # -------- URL utils -------------------------------------------------

    def _normalize_url(self, url: str) -> str:
        """
        Normalize a URL for consistent comparison and de-duplication.

        - Remove URL fragments (#...).
        - Normalize scheme/host casing.
        - Leave path/query as-is (we filter those separately).
        """
        # Remove fragment (e.g. "#section-3")
        url, _ = urldefrag(url)
        parsed = urlparse(url)

        # Normalize scheme and netloc (lowercase)
        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
        )
        return urlunparse(normalized)

    def _is_url_in_scope(self, url: str) -> bool:
        """
        Check if the given URL is within our domain and allowed path prefixes.
        """
        try:
            parsed = urlparse(url)
        except Exception:
            return False

        # Must be HTTP or HTTPS
        if parsed.scheme not in ("http", "https"):
            return False

        # Domain restriction: exact match or subdomain of allowed_domain
        # e.g. "www.consumerfinance.gov" allowed when allowed_domain="consumerfinance.gov"
        host = parsed.netloc.lower()
        allowed = self.config.allowed_domain.lower()
        if not (host == allowed or host.endswith("." + allowed)):
            return False

        # Basic path filtering
        path = parsed.path or "/"

        # Disallow paths explicitly configured as out-of-scope
        for prefix in self.config.disallowed_path_prefixes or []:
            if path.startswith(prefix):
                return False

        # Extra safety: avoid query params (e.g. ?q=search)
        if parsed.query:
            return False

        # Require that the path starts with at least one allowed prefix
        if self.config.allowed_path_prefixes:
            if not any(path.startswith(p) for p in self.config.allowed_path_prefixes):
                return False

        return True

    def _extract_links(self, base_url: str, html: str) -> List[str]:
        """
        Extract candidate links from an HTML page, converted to absolute URLs.

        We only extract <a href="..."> links and do lightweight filtering.
        """
        links: List[str] = []
        soup = BeautifulSoup(html, "lxml")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()

            # Ignore mailto:, tel:, javascript:, etc.
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue

            # Join relative links against base URL
            absolute = urljoin(base_url, href)
            links.append(absolute)

        return links

    # -------- Crawl core -------------------------------------------------

    def crawl(self) -> Iterable[CrawledPage]:
        """
        Run a BFS crawl according to the configuration.

        Yields CrawledPage objects for each successfully fetched HTML page.
        """
        queue: Deque[Tuple[str, int, Optional[str]]] = deque()

        # Initialize queue with seed URLs
        for url in self.config.start_urls:
            norm = self._normalize_url(url)
            if norm not in self._seen_urls and self._is_url_in_scope(norm):
                self._seen_urls.add(norm)
                queue.append((norm, 0, None))

        pages_fetched = 0

        while queue:
            if pages_fetched >= self.config.max_pages:
                logger.info(
                    "Reached max_pages=%d, stopping crawl",
                    self.config.max_pages,
                )
                break

            current_url, depth, parent_url = queue.popleft()

            if depth > self.config.max_depth:
                logger.debug(
                    "Skipping %s due to depth %d > max_depth=%d",
                    current_url,
                    depth,
                    self.config.max_depth,
                )
                continue

            logger.info("Crawling URL=%s depth=%d", current_url, depth)
            fetched: FetchedPage = self.fetcher.fetch(current_url)

            # Respect delay between requests
            if self.config.delay_seconds > 0:
                time.sleep(self.config.delay_seconds)

            if fetched.error is not None or fetched.text is None:
                logger.warning(
                    "Failed to fetch %s (status=%s, error=%s)",
                    current_url,
                    fetched.status_code,
                    fetched.error,
                )
                continue

            # Yield the successfully fetched page
            pages_fetched += 1
            yield CrawledPage(
                url=fetched.final_url or current_url,
                html=fetched.text,
                depth=depth,
                parent_url=parent_url,
            )

            # Extract and enqueue new links
            child_links = self._extract_links(
                base_url=fetched.final_url or current_url,
                html=fetched.text,
            )

            for child_url in child_links:
                norm_child = self._normalize_url(child_url)

                if norm_child in self._seen_urls:
                    continue

                if not self._is_url_in_scope(norm_child):
                    continue

                self._seen_urls.add(norm_child)
                queue.append((norm_child, depth + 1, current_url))
