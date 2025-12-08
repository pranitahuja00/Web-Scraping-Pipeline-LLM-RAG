# scraper_pipeline/parser.py

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import List, Optional
from bs4 import BeautifulSoup, Tag
from .crawler import CrawledPage

logger = logging.getLogger(__name__)


# Class/id/role substrings commonly used for nav, footer, sidebars, and other "chrome"
BAD_CONTAINER_HINTS = [
    "nav", "menu", "footer", "header", "sidebar", "side-bar",
    "related", "breadcrumb", "search", "site-tools", "utility"
]

# Generic heading words that are almost always navigation/help/footer content
GENERIC_HEADING_WORDS = {
    "home", "search", "about", "about us", "contact", "contact us",
    "legal", "legal disclaimer", "more", "resources", "help",
}

MIN_HEADING_LEN = 8  # skip very short generic headings


@dataclass
class ParsedPage:
    """
    Structured representation of a parsed HTML page.
    This is the clean content layer before enrichment.
    """
    url: str
    title: str
    body_text: str
    num_headings: int
    depth: int
    parent_url: Optional[str]
    headings: List[str]


def _extract_title(soup: BeautifulSoup) -> str:
    """
    Extract best page title:
    1. <title> tag (browser title)
    2. First <h1> (main visible title)
    """
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    return ""


def _choose_main_container(soup: BeautifulSoup):
    """
    Pick the main content area.

    Priority:
    1. <main> — used by modern websites
    2. <article> — used for documentation/posts
    3. Largest <div> by text length — generic fallback
    """
    main = soup.find("main")
    if main:
        return main

    article = soup.find("article")
    if article:
        return article

    best = None
    best_len = 0
    for div in soup.find_all("div"):
        text = div.get_text(strip=True)
        if text and len(text) > best_len:
            best = div
            best_len = len(text)

    return best or soup.body or soup


def _clean_text(raw_text: str) -> str:
    """
    Normalize extracted text:
    - Strip whitespace
    - Collapse multiple blank lines
    - Preserve natural paragraph structure
    """
    lines = raw_text.splitlines()
    cleaned = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # preserve single blank line but collapse multiples
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        cleaned.append(stripped)

    return "\n".join(cleaned).strip()


def _is_chrome_container(tag: Tag) -> bool:
    """
    Determine if a tag appears to be a nav/footer/sidebar container
    by checking its class/id/role/aria-label for known hint substrings.
    """
    attr_values = []

    for attr in ("class", "id", "role", "aria-label"):
        v = tag.get(attr)
        if not v:
            continue

        # classes can be lists, convert all to lowercase strings
        if isinstance(v, list):
            attr_values.extend(str(x).lower() for x in v)
        else:
            attr_values.append(str(v).lower())

    # substring match → robust to variations like "top-nav", "footer-section"
    return any(hint in value for value in attr_values for hint in BAD_CONTAINER_HINTS)


def _remove_chrome_sections(container: Tag) -> None:
    """
    Remove nav/footer/sidebar sections from the main content container.
    This prevents boilerplate "About us", "Search", etc. from appearing
    in both headings and body text across every page.
    """
    to_remove = []

    # Look at every tag inside main container
    for tag in container.find_all(True):
        if _is_chrome_container(tag):
            to_remove.append(tag)

    # Decompose after collecting to avoid altering DOM during iteration
    for tag in to_remove:
        tag.decompose()


def _heading_passes_filters(text: str) -> bool:
    """
    Keep only meaningful content headings:
    - Skip short generic ones ("Search", "More", "Home")
    - Skip known navigation/footer headings
    """
    stripped = text.strip()
    lower = stripped.lower()

    if len(stripped) < MIN_HEADING_LEN:
        return False

    if lower in GENERIC_HEADING_WORDS:
        return False

    return True


def parse_crawled_page(page: CrawledPage) -> ParsedPage:
    """
    Convert a CrawledPage (raw HTML) into a ParsedPage with:
      - Clean title
      - Extracted & cleaned headings (H1–H6)
      - Clean body text (paragraphs, lists, H2+)
      - No nav/footer/sidebar content
      - No duplicate title in body
    """
    soup = BeautifulSoup(page.html, "lxml")

    # Remove non-content tags early
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = _extract_title(soup)
    main_container = _choose_main_container(soup)
    if not main_container:
        main_container = soup

    # Remove navigation/footer/sidebar blocks
    _remove_chrome_sections(main_container)

    # Extract headings (H1–H6) after chrome removal
    heading_tags = main_container.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    headings_list = []
    num_headings = 0  # number of meaningful h1–h3

    for h in heading_tags:
        txt = h.get_text(strip=True)
        if not txt:
            continue

        if not _heading_passes_filters(txt):
            continue

        headings_list.append(txt)

        if h.name in ("h1", "h2", "h3"):
            num_headings += 1

    # Remove only the FIRST <h1> to avoid duplicating title in body text
    first_h1 = main_container.find("h1")
    if first_h1:
        first_h1.decompose()

    # Extract cleaned body text (H2+ preserved)
    raw_text = main_container.get_text(separator="\n")
    body_text = _clean_text(raw_text)

    return ParsedPage(
        url=page.url,
        title=title,
        body_text=body_text,
        num_headings=num_headings,
        depth=page.depth,
        parent_url=page.parent_url,
        headings=headings_list,
    )
