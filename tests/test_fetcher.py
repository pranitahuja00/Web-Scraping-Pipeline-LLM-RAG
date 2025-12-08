# tests/test_fetcher.py

from scraper_pipeline.fetcher import Fetcher
import logging

# Basic logging setup so we can see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

def main():
    fetcher = Fetcher()

    # 1. Test a valid URL
    url_ok = "https://www.consumerfinance.gov/ask-cfpb/what-laws-limit-what-debt-collectors-can-say-or-do-en-329/"
    page_ok = fetcher.fetch(url_ok)
    print("\n=== TEST 1: Valid URL ===")
    print("URL:        ", url_ok)
    print("Status code:", page_ok.status_code)
    print("Final URL:  ", page_ok.final_url)
    print("Error:      ", page_ok.error)
    if page_ok.text:
        print("Body snippet:", page_ok.text[:300].replace("\n", " "), "...\n")

    # 2. Test a likely 404
    url_404 = "https://docs.python.org/3/this-page-does-not-exist"
    page_404 = fetcher.fetch(url_404)
    print("\n=== TEST 2: 404 URL ===")
    print("URL:        ", url_404)
    print("Status code:", page_404.status_code)
    print("Final URL:  ", page_404.final_url)
    print("Error:      ", page_404.error)
    print("Body snippet:", (page_404.text or "")[:200].replace("\n", " "), "...\n")

    # 3. Test a clearly invalid domain (to trigger network error)
    url_bad = "https://ClickHereToWinMoney.com/"
    page_bad = fetcher.fetch(url_bad)
    print("\n=== TEST 3: Bad Domain ===")
    print("URL:        ", url_bad)
    print("Status code:", page_bad.status_code)
    print("Final URL:  ", page_bad.final_url)
    print("Error:      ", page_bad.error)

if __name__ == "__main__":
    main()
