# tests/test_crawler.py

import logging

from scraper_pipeline.fetcher import Fetcher
from scraper_pipeline.crawler import Crawler, CrawlConfig

# Basic logging so you can see what the crawler is doing
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


def main():
    # Use the same Fetcher you already tested
    fetcher = Fetcher()

    # Configuration specifically for CFPB "Ask CFPB" credit card answers
    config = CrawlConfig(
        allowed_domain="consumerfinance.gov",
        start_urls=[
            # Listing page for credit card answers
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
        max_depth=2,       # don't go too deep for the test
        max_pages=5,       # small number just to see it working
        delay_seconds=0.5, # be polite
    )

    crawler = Crawler(fetcher=fetcher, config=config)

    print("\n=== Starting crawler test ===\n")

    count = 0
    for page in crawler.crawl():
        count += 1
        print("\n-----------------------------")
        print(f"[{count}] URL: {page.url}")
        print(f"    Depth:  {page.depth}")
        print(f"    Parent: {page.parent_url}")
        snippet = page.html[:200].replace("\n", " ")
        print(f"    HTML snippet: {snippet} ...\n")
        print("\n-----------------------------")

    print(f"\nCrawl Test Successful, fetched {count} pages.\n")


if __name__ == "__main__":
    main()
