# tests/test_writer.py

import logging
from itertools import islice
from pathlib import Path
from scraper_pipeline.fetcher import Fetcher
from scraper_pipeline.crawler import Crawler, CrawlConfig
from scraper_pipeline.parser import parse_crawled_page
from scraper_pipeline.enrich import build_document
from scraper_pipeline.writer import write_documents_jsonl

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
        max_depth=2,
        max_pages=5,   # grab a few docs for the JSONL test
        delay_seconds=0.5,
    )

    crawler = Crawler(fetcher=fetcher, config=config)

    print("\n=== Starting writer test (full pipeline → JSONL) ===\n")

    documents = []
    for crawled_page in islice(crawler.crawl(), 5):
        parsed = parse_crawled_page(crawled_page)
        doc = build_document(parsed)
        documents.append(doc)

    # Choose an output path under the project directory
    output_path = Path("output_data") / "cfpb_documents_test.jsonl"
    output_file = write_documents_jsonl(documents, output_path)

    print("Wrote", len(documents), "documents to:", str(output_file))

    # Show the first few lines for sanity check
    print("\nFirst few lines from the JSONL file:\n")

    with output_file.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 3:
                break
            print(line.rstrip())

    print("\nWriter test completed.\n")


if __name__ == "__main__":
    main()
