# tests/test_enrich.py

import logging
from itertools import islice
from scraper_pipeline.fetcher import Fetcher
from scraper_pipeline.crawler import Crawler, CrawlConfig
from scraper_pipeline.parser import parse_crawled_page
from scraper_pipeline.enrich import build_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def main():
    fetcher = Fetcher()

    config = CrawlConfig(
        allowed_domain="consumerfinance.gov",
        start_urls=[
            "https://www.consumerfinance.gov/ask-cfpb/",
        ],
        allowed_path_prefixes=[
            "/consumer-tools/credit-cards/answers/",
            "/ask-cfpb/",
        ],
        disallowed_path_prefixes=[
            "/ask-cfpb/search",
            "/askcfpb/search",
        ],
        max_depth=1,   # shallow for test
        max_pages=3,   # just a few docs
        delay_seconds=0.5,
    )

    crawler = Crawler(fetcher=fetcher, config=config)

    print("\n=== Starting enrichment test ===\n")

    for i, crawled_page in enumerate(islice(crawler.crawl(), 3), start=1):
        parsed = parse_crawled_page(crawled_page)
        doc = build_document(parsed)

        serial = doc.to_serializable_dict()

        print(f"[{i}] ID: {doc.id}")
        print(f"    URL:          {doc.url}")
        print(f"    Source domain:{doc.source_domain}")
        print(f"    Depth:        {doc.crawl_depth}")
        print(f"    Title:        {doc.title!r}")
        print(f"    Content type: {doc.content_type}")
        print(f"    Language:     {doc.language}")
        print(f"    Word count:   {doc.word_count}")
        print(f"    Read time:    {doc.estimated_reading_time_min} min")
        print(f"    Number of Headings:     {doc.num_headings}")
        print(f"    Extra Metadata:     {doc.extra_metadata}")
        print(f"    Topical tags: {doc.topical_tags}")
        print(f"    Fetched at:   {serial['fetched_at']}")
        body_snippet = doc.body_text[:300].replace("\n", " ")
        print(f"    Body snippet: {body_snippet} ...\n")

    print("Enrichment test completed.\n")


if __name__ == "__main__":
    main()
