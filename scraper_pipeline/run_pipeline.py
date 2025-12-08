#!/usr/bin/env python
"""
End-to-end runner for the scraping → parsing → enrichment → JSONL pipeline.

Usage examples:

    # Use the CFPB profile (defined in config_runtime_profiles.py)
    python -m scraper_pipeline.run_pipeline --profile cfpb

    # Override output path and max pages
    python -m scraper_pipeline.run_pipeline --profile cfpb \
        --output output_data/cfpb_full.jsonl \
        --max-pages 100

    # Dry run: crawl a few pages, print info, no JSONL written
    python -m scraper_pipeline.run_pipeline --profile cfpb --dry-run

    # No profile: specify a single start URL directly
    python -m scraper_pipeline.run_pipeline \
        --url https://www.consumerfinance.gov/ask-cfpb/ \
        --allowed-path-prefix /ask-cfpb \
        --max-pages 30 \
        --output output_data/cfpb_direct.jsonl
"""

from __future__ import annotations

import argparse
import logging
from itertools import islice
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlparse

from scraper_pipeline.fetcher import Fetcher
from scraper_pipeline.crawler import Crawler, CrawlConfig
from scraper_pipeline.parser import parse_crawled_page
from scraper_pipeline.enrich import build_document
from scraper_pipeline.writer import write_documents_jsonl
from scraper_pipeline.config_runtime_profiles import CRAWL_PROFILES

logger = logging.getLogger(__name__)

# Safety cap to avoid accidentally hammering a server
MAX_PAGES_HARD_CAP = 500


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the pipeline runner.

    Two modes:
      - Profile mode: --profile <name>
      - Direct URL mode: --url <start_url>

    Exactly one of --profile or --url is required.
    """
    parser = argparse.ArgumentParser(
        description="Run the web scraping → enrichment pipeline using a profile or a direct URL."
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--profile",
        choices=sorted(CRAWL_PROFILES.keys()),
        help="Name of the crawl profile to use (defined in config_runtime_profiles.py).",
    )
    group.add_argument(
        "--url",
        type=str,
        help=(
            "Start URL to crawl when not using a profile. "
            "The allowed_domain will be inferred from this URL."
        ),
    )

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=(
            "Output JSONL file path. "
            "If not provided: for profiles, may use profile['default_output']; "
            "otherwise falls back to output_data/documents.jsonl."
        ),
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional override for max_pages (both profile and URL modes).",
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Optional override for max_depth (both profile and URL modes).",
    )

    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=None,
        help="Optional override for delay_seconds (both profile and URL modes).",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Dry run mode: crawl a small number of pages, print parsed/enriched "
            "info to console, and do NOT write a JSONL file."
        ),
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR). Default: INFO.",
    )

    parser.add_argument(
    "--allowed-path-prefix",
    action="append",
    default=None,
    help="Allowed URL path prefixes when using direct URL mode. Can be specified multiple times.",
    )

    parser.add_argument(
    "--disallowed-path-prefix",
    action="append",
    default=None,
    help="Disallowed URL path prefixes when using direct URL mode. Can be specified multiple times.",
    )


    return parser.parse_args()


def _apply_max_pages_cap(max_pages: int) -> int:
    """
    Enforce a hard safety cap on max_pages to avoid hammering servers.
    """
    if max_pages <= 0:
        raise ValueError("max_pages must be positive.")
    if max_pages > MAX_PAGES_HARD_CAP:
        logger.warning(
            "Requested max_pages=%d exceeds hard cap of %d. Capping to %d.",
            max_pages,
            MAX_PAGES_HARD_CAP,
            MAX_PAGES_HARD_CAP,
        )
        return MAX_PAGES_HARD_CAP
    return max_pages


def build_crawl_config_from_profile(
    profile_name: str, args: argparse.Namespace
) -> tuple[CrawlConfig, dict]:
    """
    Construct a CrawlConfig from the selected profile plus any CLI overrides.
    Returns:
      (crawl_config, profile_dict)
    """
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

    max_pages = _apply_max_pages_cap(max_pages)

    logger.info(
        "Using profile '%s' crawl config: domain=%s, start_urls=%s, "
        "max_depth=%s, max_pages=%s, delay_seconds=%s",
        profile_name,
        allowed_domain,
        start_urls,
        max_depth,
        max_pages,
        delay_seconds,
    )

    crawl_config = CrawlConfig(
        allowed_domain=allowed_domain,
        start_urls=start_urls,
        allowed_path_prefixes=allowed_path_prefixes,
        disallowed_path_prefixes=disallowed_path_prefixes,
        max_depth=max_depth,
        max_pages=max_pages,
        delay_seconds=delay_seconds,
    )
    return crawl_config, profile


def build_crawl_config_from_url(args: argparse.Namespace) -> CrawlConfig:
    """
    Construct a CrawlConfig directly from a provided URL + CLI overrides.
    - allowed_domain inferred from URL host
    - start_urls = [url]
    - allowed_path_prefixes controlled by CLI
    - disallowed_path_prefixes controlled by CLI
    """
    if not args.url:
        raise ValueError("URL mode requires --url.")

    parsed = urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL provided: {args.url}")

    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[len("www.") :]

    allowed_domain = host
    start_urls = [args.url]

    # If user did not supply allowed prefixes → allow entire domain
    allowed_path_prefixes = (
        args.allowed_path_prefix if args.allowed_path_prefix is not None else []
    )

    disallowed_path_prefixes = (
        args.disallowed_path_prefix if args.disallowed_path_prefix is not None else []
    )

    # Defaults if not overridden
    max_depth = args.max_depth if args.max_depth is not None else 1
    max_pages = args.max_pages if args.max_pages is not None else 50
    delay_seconds = args.delay_seconds if args.delay_seconds is not None else 0.5

    max_pages = _apply_max_pages_cap(max_pages)

    logger.info(
        "Using URL-based crawl config: domain=%s, start_url=%s, "
        "allowed_path_prefixes=%s, disallowed_path_prefixes=%s, "
        "max_depth=%s, max_pages=%s, delay_seconds=%s",
        allowed_domain,
        start_urls,
        allowed_path_prefixes,
        disallowed_path_prefixes,
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
    """
    for crawled_page in crawler.crawl():
        parsed = parse_crawled_page(crawled_page)
        doc = build_document(parsed)
        yield doc


def run_dry_run(crawler: Crawler, max_preview: int = 5) -> None:
    """
    Dry-run mode:
    - Process up to `max_preview` pages
    - Print URL, title, topical tags, headings, and a body snippet
    - Do NOT write JSONL
    """
    logger.info("Running in DRY-RUN mode (max_preview=%d)", max_preview)

    count = 0
    for crawled_page in islice(crawler.crawl(), max_preview):
        parsed = parse_crawled_page(crawled_page)
        doc = build_document(parsed)
        count += 1

        print("\n-----------------------------")
        print(f"    ID:           {doc.id}")
        print(f"    URL:          {doc.url}")
        print(f"    Source domain:{doc.source_domain}")
        print(f"    Depth:        {doc.crawl_depth}")
        print(f"    Title:        {doc.title!r}")
        print(f"    Content type: {doc.content_type}")
        print(f"    Language:     {doc.language}")
        print(f"    Word count:   {doc.word_count}")
        print(f"    Read time:    {doc.estimated_reading_time_min} min")
        print(f"    Number of Headings: {doc.num_headings}")
        print(f"    Extra Metadata: {doc.extra_metadata}")
        print(f"    Topical tags: {doc.topical_tags}")
        body_snippet = doc.body_text[:300].replace("\n", " ")
        print(f"    Body snippet: {body_snippet} ...\n")
        print("-----------------------------\n")

    logger.info("Dry run processed %d page(s). No output file written.", count)


def _resolve_output_path(
    args: argparse.Namespace,
    profile: Optional[dict] = None,
) -> Path:
    """
    Decide the output path priority:
      1) If --output is provided, use that.
      2) Else if profile has 'default_output', use that.
      3) Else fallback to 'output_data/documents.jsonl'.
    """
    if args.output:
        return Path(args.output)

    if profile is not None and "default_output" in profile:
        return Path(profile["default_output"])

    return Path("output_data/documents.jsonl")


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

    if args.profile:
        logger.info("Starting pipeline in PROFILE mode: profile=%s", args.profile)
        crawl_config, profile = build_crawl_config_from_profile(args.profile, args)
        output_path = _resolve_output_path(args, profile)
    else:
        logger.info("Starting pipeline in URL mode: url=%s", args.url)
        crawl_config = build_crawl_config_from_url(args)
        output_path = _resolve_output_path(args, profile=None)

    fetcher = Fetcher()
    crawler = Crawler(fetcher=fetcher, config=crawl_config)

    if args.dry_run:
        run_dry_run(crawler, max_preview=5)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Beginning crawl and document generation...")

    docs = list(generate_documents(crawler))
    num_docs = len(docs)

    if num_docs == 0:
        logger.warning("No documents were generated; no JSONL file will be written.")
        return

    output_file = write_documents_jsonl(documents=docs, output_path=output_path)

    logger.info(
        "Pipeline completed. Wrote %d document(s) to %s (max_pages=%d).",
        num_docs,
        output_file,
        crawl_config.max_pages,
    )


if __name__ == "__main__":
    main()
