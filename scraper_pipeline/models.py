# scraper_pipeline/models.py

from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional

@dataclass
class Document:
    """
    This class is a normalized representation of a single web page after crawling, parsing, cleaning, and enrichment
    """

    # 1. Identity
    id: str
    url: str
    source_domain: str

    # 2. Core content
    title: str
    body_text: str

    # 3. Crawl & origin metadata
    fetched_at: datetime
    crawl_depth: int
    parent_url: Optional[str] = None

    # 4. High-level classification
    content_type: str = "unknown"  # e.g. "help_article", "faq", "docs_page", "blog_post"
    language: str = "unknown"      # e.g. "en", "es"

    # 5. Quality / ranking signals
    word_count: int = 0
    char_count: int = 0
    estimated_reading_time_min: float = 0.0
    num_headings: int = 0
    has_code_blocks: bool = False

    # 6. Credit-servicing specific info
    topical_tags: List[str] = None  # e.g. ["payments", "late_fees", "hardship"]

    # 7. Arbitrary extra metadata (flexible extension)
    extra_metadata: Dict[str, Any] = None

    def __post_init__(self) -> None:
        # Ensure lists/dicts are not shared across instances.
        if self.topical_tags is None:
            self.topical_tags = []
        if self.extra_metadata is None:
            self.extra_metadata = {}

        # If word/char counts weren't set, derive them from body_text.
        if self.word_count == 0 and self.body_text:
            self.word_count = len(self.body_text.split())

        if self.char_count == 0 and self.body_text:
            self.char_count = len(self.body_text)

        # If reading time wasn't set, approximate: 200 words/min.
        if self.estimated_reading_time_min == 0.0 and self.word_count > 0:
            self.estimated_reading_time_min = round(self.word_count / 200.0, 2)

    def to_serializable_dict(self) -> Dict[str, Any]:
        """
        Convert the Document into a JSON-serializable dict
        """
        d = asdict(self)
        if isinstance(self.fetched_at, datetime):
            d["fetched_at"] = self.fetched_at.isoformat() # Datetime fields are converted to ISO 8601 strings.
        return d
