# tests/test_parser.py

import logging
from itertools import islice

from scraper_pipeline.fetcher import Fetcher
from scraper_pipeline.crawler import Crawler, CrawlConfig
from scraper_pipeline.parser import parse_crawled_page

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def main():
    fetcher = Fetcher()

    config = CrawlConfig(
        allowed_domain="consumerfinance.gov",
        start_urls=[
            "https://www.consumerfinance.gov/consumer-tools/credit-cards/answers/",
        ],
        allowed_path_prefixes=[
            "/consumer-tools/credit-cards/answers/",
            "/ask-cfpb/",
        ],
        disallowed_path_prefixes=[
            "/ask-cfpb/search",
            "/askcfpb/search",
        ],
        max_depth=1,   # keep it shallow for this test
        max_pages=3,   # only need a few pages
        delay_seconds=0.5,
    )

    crawler = Crawler(fetcher=fetcher, config=config)

    print("\n=== Starting parser test ===\n")

    # Take just the first few crawled pages
    for i, crawled_page in enumerate(islice(crawler.crawl(), 3), start=1):
        parsed = parse_crawled_page(crawled_page)

        print(f"[{i}] URL: {parsed.url}")
        print(f"    Depth:  {parsed.depth}")
        print(f"    Title:  {parsed.title!r}")
        print(f"    Headings: {parsed.num_headings}")
        print(f"    Has code blocks: {parsed.has_code_blocks}")

        snippet = parsed.body_text[:400].replace("\n", " ")
        print(f"    Body snippet: {snippet} ...\n")

    print("Parser test completed.\n")


if __name__ == "__main__":
    main()
