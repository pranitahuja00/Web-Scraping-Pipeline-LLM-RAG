# scraper_pipeline/config_profiles.py
"""
Crawl profiles:
Define site-specific crawling settings.
Used by run_pipeline.py to construct CrawlConfig.
"""

CRAWL_PROFILES = {
    "cfpb": {
        "allowed_domain": "consumerfinance.gov",
        "start_urls": [
            "https://www.consumerfinance.gov/ask-cfpb/",
        ],
        "allowed_path_prefixes": [
            "/consumer-tools/credit-cards/answers/",
            "/ask-cfpb/",
        ],
        "disallowed_path_prefixes": [
            "/ask-cfpb/search",
            "/askcfpb/search",
        ],
        "max_depth": 2,
        "max_pages": 200,
        "delay_seconds": 0.5,
    },

    # Add more profiles here...
}
