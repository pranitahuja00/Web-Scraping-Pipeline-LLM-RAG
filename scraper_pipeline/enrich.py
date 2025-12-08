# scraper_pipeline/enrich.py

from __future__ import annotations
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import List
from urllib.parse import urlparse
from .models import Document
from .parser import ParsedPage
from langdetect import detect, LangDetectException
from .config_behavior import TOPIC_KEYWORDS


# --- Simple language detection ---------------------------------------------


def _detect_language(text: str) -> str:
    if not text or len(text.strip()) < 20:
        return "unknown"
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"
    

# --- Content type classification -------------------------------------------

def _classify_content_type(url: str, body_text: str, num_headings: int) -> str:
    """
    Very simple rule-based classification for content_type.

    For the CFPB setup:
    - URLs under /consumer-tools/credit-cards/answers/ are listing pages
    - URLs under /ask-cfpb/ are Q&A / FAQ-like
    - Fallback to "article"
    """
    parsed = urlparse(url)
    path = parsed.path or "/"

    if path.startswith("/consumer-tools/credit-cards/answers/"):
        return "listing_page"

    if path.startswith("/ask-cfpb/"):
        # Q&A style content
        return "faq"

    # Generic fallback based on length
    if len(body_text.split()) > 300 and num_headings >= 2:
        return "article"

    return "unknown"


def _infer_topical_tags(title: str, body_text: str) -> List[str]:
    """
    Assign coarse topical tags based on keyword presence in title/body_text.

    These tags are directly useful for Krew-style credit-servicing agents:
    - Boosting relevant docs when a user asks about payments, hardship, etc.
    """
    text = f"{title}\n{body_text}".lower()
    tags = []

    for tag, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                tags.append(tag)
                break  # don't need multiple keyword hits per tag

    # Remove duplicates while preserving order
    seen = set()
    deduped = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            deduped.append(t)

    return deduped


# --- ID + domain helpers ---------------------------------------------------

def _generate_id_from_url(url: str) -> str:
    """
    Stable ID derived from a normalized URL using SHA-256.

    This ensures:
    - Idempotent crawls (same URL -> same ID)
    - Easy upserts in downstream systems
    """
    normalized = url.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_domain(url: str) -> str:
    """
    Extract the source domain from a URL, without scheme.

    e.g. "https://www.consumerfinance.gov/..." -> "consumerfinance.gov"
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if host.startswith("www."):
        host = host[len("www.") :]

    return host or "unknown"


# --- Main builder ----------------------------------------------------------

def build_document(parsed: ParsedPage) -> Document:
    """
    Convert a ParsedPage into a fully-enriched Document.

    Enrichment includes:
    - Stable ID from URL
    - Source domain
    - Fetched timestamp (now)
    - Language heuristic
    - Content type classification
    - Topical tags (credit-servicing)
    - word_count, char_count, estimated_reading_time_min
      (Document.__post_init__ will compute these if left as 0)
    """
    title = parsed.title or ""
    body_text = parsed.body_text or ""

    language = _detect_language(body_text)
    content_type = _classify_content_type(
        url=parsed.url,
        body_text=body_text,
        num_headings=parsed.num_headings,
    )
    topical_tags = _infer_topical_tags(title=title, body_text=body_text)

    extra_metadata = {
        "headings": parsed.headings,
    }

    doc = Document(
        id=_generate_id_from_url(parsed.url),
        url=parsed.url,
        source_domain=_extract_domain(parsed.url),
        title=title,
        body_text=body_text,
        fetched_at=datetime.utcnow(),  # we could also pass this from crawler
        crawl_depth=parsed.depth,
        parent_url=parsed.parent_url,
        content_type=content_type,
        language=language,
        num_headings=parsed.num_headings,
        topical_tags=topical_tags,
        extra_metadata=extra_metadata
        # word_count, char_count, estimated_reading_time_min will be
        # computed automatically in Document.__post_init__ if left as 0.
    )

    return doc
