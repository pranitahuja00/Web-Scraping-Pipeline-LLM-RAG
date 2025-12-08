# scraper_pipeline/parser.py

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import List, Optional
from bs4 import BeautifulSoup
from .crawler import CrawledPage

logger = logging.getLogger(__name__)


@dataclass
class ParsedPage:
    """
    Result of parsing a CrawledPage's HTML into structured text.

    This is an intermediate representation; later we'll turn ParsedPage into
    a full Document with IDs, timestamps, and enrichment.
    """

    url: str
    title: str
    body_text: str
    num_headings: int
    depth: int
    parent_url: Optional[str]
    headings: List[str]  # All headings (h1–h6) as plain strings


def _extract_title(soup: BeautifulSoup) -> str:
    """
    Extract a reasonable title from the HTML.

    Priority:
    1) <title> tag
    2) First <h1>
    3) Fallback to empty string
    """
    # <title> in <head>
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    # First <h1> in body
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    return ""


def _choose_main_container(soup: BeautifulSoup):
    """
    Heuristic to choose the main content container.

    Strategy:
    1) Prefer <main> if present
    2) Then <article>
    3) Else, choose the <div> with the largest text length
    """
    # Prefer <main>
    main = soup.find("main")
    if main:
        return main

    # Then <article>
    article = soup.find("article")
    if article:
        return article

    # Fallback: choose the <div> with the most text
    candidates = soup.find_all("div")
    best = None
    best_len = 0
    for div in candidates:
        text = div.get_text(strip=True)
        if not text:
            continue
        if len(text) > best_len:
            best_len = len(text)
            best = div

    return best or soup.body or soup  # last resort fallback


def _clean_text(raw_text: str) -> str:
    """
    Normalize whitespace and remove obviously empty lines.

    - Collapse multiple blank lines.
    - Strip leading/trailing spaces per line.
    """
    lines = raw_text.splitlines()
    cleaned_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # keep at most one blank line in a row
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue
        cleaned_lines.append(stripped)

    # Join lines using newline; consecutive blank lines already collapsed.
    return "\n".join(cleaned_lines).strip()


def parse_crawled_page(page: CrawledPage) -> ParsedPage:
    """
    Parse a CrawledPage (HTML) into a ParsedPage (clean text + metadata).

    Steps:
    - Remove scripts/styles/noscript.
    - Extract title.
    - Choose a main content container (main/article/div).
    - Collect all headings (h1–h6) into a list.
    - Remove only the first <h1> from the container (to avoid duplicating title).
    - Extract text, normalize whitespace.
    - Compute num_headings.
    """
    html = page.html
    soup = BeautifulSoup(html, "lxml")

    # Remove scripts, styles, and noscript elements.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    # Extract title from <title> or first <h1>
    title = _extract_title(soup)

    # Choose main content container
    main_container = _choose_main_container(soup)
    if not main_container:
        logger.warning("No main container found for URL %s", page.url)
        main_container = soup

    # --- Extract all headings (h1–h6) before mutating the container ---
    heading_tags = main_container.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
    headings_list: List[str] = [
        h.get_text(strip=True)
        for h in heading_tags
        if h.get_text(strip=True)
    ]

    # --- Remove only the first <h1> so it doesn't appear in body_text ---
    first_h1 = main_container.find("h1")
    if first_h1:
        first_h1.decompose()

    # --- Extract text from the remaining content ---
    # H2+ headings still remain and will appear in body_text, which is good
    # for structure and retrieval.
    raw_text = main_container.get_text(separator="\n")
    body_text = _clean_text(raw_text)

    # --- Count headings (h1–h3) using the original heading tags ---
    num_headings = sum(
        1
        for h in heading_tags
        if h.name in ("h1", "h2", "h3")
    )

    return ParsedPage(
        url=page.url,
        title=title,
        body_text=body_text,
        num_headings=num_headings,
        depth=page.depth,
        parent_url=page.parent_url,
        headings=headings_list,
    )
