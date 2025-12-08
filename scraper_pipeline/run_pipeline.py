#!/usr/bin/env python
"""
End-to-end runner for the scraping → parsing → enrichment → JSONL pipeline.

Usage examples:

    # Use the CFPB credit-cards profile, write to default output path
    python -m scraper_pipeline.run_pipeline --profile cfpb

    # Override output path and max pages
    python -m scraper_pipeline.run_pipeline --profile cfpb \
        --output output_data/cfpb_full.jsonl \
        --max-pages 100

This script:
    1. Loads a crawl profile from scraper_pipeline.config_profiles
    2. Constructs a CrawlConfig
    3. Streams pages through:
       Fetcher → Crawler → Parser → Enrich → Writer(JSONL)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable

from scraper_pipeline.fetcher import Fetcher
from scraper_pipeline.crawler import Crawler, CrawlConfig
from scraper_pipeline.parser import parse_crawled_page
from scraper_pipeline.enrich import build_document
from scraper_pipeline.writer import write_documents_jsonl
from scraper_pipeline.config_runtime_profiles import CRAWL_PROFILES


logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the pipeline runner.
    """
    parser = argparse.ArgumentParser(
        description="Run the web scraping → enrichment pipeline for a given profile."
    )

    parser.add_argument(
        "--profile",
        required=True,
        choices=sorted(CRAWL_PROFILES.keys()),
        help="Name of the crawl profile to use (defined in config_profiles.py).",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="output_data/documents.jsonl",
        help="Output JSONL file path (default: output_data/documents.jsonl).",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional override for max_pages from the profile.",
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Optional override for max_depth from the profile.",
    )

    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=None,
        help="Optional override for delay_seconds from the profile.",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.",
    )

    return parser.parse_args()


def build_crawl_config(profile_name: str, args: argparse.Namespace) -> CrawlConfig:
    """
    Construct a CrawlConfig from the selected profile plus any CLI overrides.
    """
    if profile_name not in CRAWL_PROFILES:
        raise ValueError(f"Unknown profile: {profile_name}")

    profile = CRAWL_PROFILES[profile_name]

    # Start from profile defaults
    allowed_domain = profile["allowed_domain"]
    start_urls = profile["start_urls"]
    allowed_path_prefixes = profile.get("allowed_path_prefixes", [])
    disallowed_path_prefixes = profile.get("disallowed_path_prefixes", [])
    max_depth = profile.get("max_depth", 2)
    max_pages = profile.get("max_pages", 100)
    delay_seconds = profile.get("delay_seconds", 0.5)

    # Apply overrides from CLI if provided
    if args.max_depth is not None:
        max_depth = args.max_depth
    if args.max_pages is not None:
        max_pages = args.max_pages
    if args.delay_seconds is not None:
        delay_seconds = args.delay_seconds

    logger.info(
        "Using crawl config: domain=%s, start_urls=%s, max_depth=%s, "
        "max_pages=%s, delay_seconds=%s",
        allowed_domain,
        start_urls,
        max_depth,
        max_pages,
        delay_seconds,
    )

    return CrawlConfig(
        allowed_domain=allowed_domain,
        start_urls=start_urls,
        allowed_path_prefixes=allowed_path_prefixes,
        disallowed_path_prefixes=disallowed_path_prefixes,
        max_depth=max_depth,
        max_pages=max_pages,
        delay_seconds=delay_seconds,
    )


def generate_documents(crawler: Crawler) -> Iterable:
    """
    Generator that streams the full pipeline:
        CrawledPage -> ParsedPage -> Document

    This keeps memory usage low: we never need to hold all pages in a list.
    """
    for crawled_page in crawler.crawl():
        parsed = parse_crawled_page(crawled_page)
        doc = build_document(parsed)
        yield doc


def main() -> None:
    args = parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    logger.info("Starting pipeline with profile=%s", args.profile)

    # Build crawl configuration from profile + overrides
    crawl_config = build_crawl_config(args.profile, args)

    # Initialize pipeline components
    fetcher = Fetcher()
    crawler = Crawler(fetcher=fetcher, config=crawl_config)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Run the streaming pipeline and write to JSONL
    logger.info("Beginning crawl and document generation...")
    output_file = write_documents_jsonl(
        documents=generate_documents(crawler),
        output_path=output_path,
    )

    logger.info("Pipeline completed. Output written to: %s", output_file)


if __name__ == "__main__":
    main()
