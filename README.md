## !! This personal project is only meant for research and educational purposes; it is not meant for any commercial or republishing purposes !!

# Web Document Scraper & AI-Enrichment Pipeline

This project implements a modular, extensible web-scraping pipeline designed for AI knowledge ingestion, especially for credit-servicing use cases. It crawls selected public websites, extracts meaningful content, enriches it with metadata for downstream LLM workflows, and outputs JSONL documents suitable for vector databases or retrieval pipelines.

---

# Site Chosen and Why

The primary site selected for demonstration is:

Consumer Financial Protection Bureau (CFPB)  
https://www.consumerfinance.gov/

Why CFPB?

- It is a U.S. government website with publicly available educational content.
- Contains high-quality Q&A covering credit cards, loans, hardship, payments, disputes, and general credit-servicing topics.
- Ideal for powering an AI credit-servicing agent, because responses must align with government-approved guidance.
- The site is structured, consistent, and safe to crawl with basic politeness measures.

The scraper is not limited to CFPB. It supports:

- Profiles for domain-specific crawling  
- URL mode for crawling any page within a domain with path-filtering  

---

# How to Run the Scraper

The scraper can run in two modes:

1. Direct Python execution (raw pipeline)  
2. Docker execution (no dependencies needed locally)

Both modes support:

- Profile mode  
- URL mode  

---

# 1. Running the Raw Pipeline (Python)

## A. Install Dependencies

Create and activate a virtual environment:

    python3 -m venv krew-web-scraper
    source krew-web-scraper/bin/activate
    pip install -r requirements.txt

---

# Profile Mode (Python)

Profiles are located in:

scraper_pipeline/config_runtime_profiles.py

Run using a profile:

    python -m scraper_pipeline.run_pipeline --profile cfpb

Override settings:

    python -m scraper_pipeline.run_pipeline --profile cfpb --max-pages 50 --max-depth 2 --output output_data/cfpb_sample.jsonl

Dry run (does not save output):

    python -m scraper_pipeline.run_pipeline --profile cfpb --dry-run

---

# URL Mode (Python)

    python -m scraper_pipeline.run_pipeline --url https://www.consumerfinance.gov/consumer-tools/credit-cards/answers/ --allowed-path-prefix /consumer-tools/credit-cards/answers/ --max-depth 1 --max-pages 20 --output output_data/cfpb_url.jsonl

Dry run:

    python -m scraper_pipeline.run_pipeline --url https://example.com/info/start --dry-run

---

# 2. Running the Scraper via Docker

Build the image:

    docker build -t webdoc_scraper .

Run using a profile:

    docker run --rm -v "$(pwd)/output_data:/app/output_data" webdoc_scraper --profile cfpb

Run with overrides:

    docker run --rm -v "$(pwd)/output_data:/app/output_data" webdoc_scraper --profile cfpb --max-pages 30 --output output_data/cfpb_30.jsonl

URL mode:

    docker run --rm -v "$(pwd)/output_data:/app/output_data" webdoc_scraper --url https://www.consumerfinance.gov/consumer-tools/credit-cards/answers/ --allowed-path-prefix /consumer-tools/credit-cards/answers/ --max-pages 10 --output output_data/from_url.jsonl

---

# Data Schema (JSONL Output)

Each output line is one JSON document with the following fields:

| Field | Description |
|-------|-------------|
| id | SHA-256 hash of content for deduplication |
| url | Canonical URL of the crawled page |
| source_domain | Extracted domain |
| crawl_depth | BFS crawl depth |
| title | Extracted page title |
| body_text | Cleaned, readable main content |
| content_type | Heuristic page type |
| language | Stopword-based English detection |
| word_count | Word count of content |
| estimated_reading_time_min | Approximate reading time |
| headings | Structured meaningful headings |
| num_headings | Count of extracted headings |
| topical_tags | Keyword-based tags for domain relevance |
| extra_metadata | Additional enrichment fields |
| fetched_at | Timestamp of fetch |

Default output path if not specified:

output_data/documents.jsonl

Profiles may override via "default_output".

---

# Design Decisions

## 1. Page Selection and Crawl Strategy

BFS was selected because it provides broad, uniform exploration and prevents overly deep crawling. Combined with max_pages and max_depth, it ensures predictable behavior.

URL filtering ensures only relevant parts of the domain are crawled. Profiles and URL mode both support allowed and disallowed path prefixes to keep crawls domain-relevant.

---

## 2. Main Content Extraction

### Removal of Chrome Elements

Elements with class or id containing nav, menu, footer, sidebar, related, breadcrumb are removed. These consistently represent interface chrome rather than page content.

### Heading Filtering

Headings are retained only if they exceed a minimum length, are not generic navigation headings, and do not match common boilerplate like "About us" or "Resources". This provides meaningful structure for downstream AI tasks.

### Body Cleaning

Scripts, styles, navigation blocks, and boilerplate sections are removed. Only human-readable main content remains, making it suitable for embeddings and retrieval.

---

## 3. Metadata and AI-Oriented Enrichment

Keyword dictionaries assign topical tags for themes such as payments, late fees, hardship, disputes, interest, auto loans, home loans, student loans, refinancing, and debt consolidation.

Language is detected via stopword heuristics for robustness across short documents.

Word count, reading time, heading structure, and content type provide useful signals for ranking and retrieval workflows.

SHA-256 content hashing ensures stable deduplication across runs and sources.

---

## 4. Error Handling

Fetcher errors (timeouts, non-200 responses) are logged and skipped without interrupting the pipeline.

Crawl safety limits include max_pages, max_depth, allowed domain restriction, disallowed prefixes, and a hard global max_pages cap.

Parser fallbacks gracefully handle malformed HTML.

---

## 5. Modular Architecture and Tests

Modules:

- fetcher.py: HTTP fetching  
- crawler.py: BFS crawling and URL filtering  
- parser.py: Content extraction and cleaning  
- enrich.py: Metadata creation and topical tagging  
- writer.py: JSONL serialization  
- config_behavior.py: Rules for parser and enrichment  
- config_runtime_profiles.py: Crawl profiles

Unit tests validate:

- fetcher returns valid responses  
- crawler respects URL rules  
- parser extracts meaningful content  
- enrichment fields are computed correctly  
- writer generates valid JSONL output  

---

# Future Work

Future improvements suitable for production:

- robots.txt compliance  
- Scheduled crawling using cron, Airflow, or Prefect  
- Monitoring extract quality and crawl anomalies  
- Cross-source deduplication using similarity measures  
- Extraction of structured financial information (interest rates, fee tables)  
- Automatic insertion of documents into vector databases  
- Embedding-based topic classification instead of keyword-based tagging  

---


