# scraper_pipeline/config.py
"""
Central configuration for scraper_pipeline. This file contains all tunable lists, keywords, and heuristics used by
parser.py and enrich.py.

Config is organized into two sections:
1. PARSER CONFIG  -> controls HTML parsing behavior
2. ENRICH CONFIG  -> controls AI enrichment & topical tagging
"""

from __future__ import annotations
from typing import Dict, List, Set


# ======================================================================
# ============================ PARSER CONFIG ============================
# ======================================================================

"""
Configuration used ONLY by parser.py to:
- Remove nav/footer/sidebar chrome
- Filter headings
- Identify unwanted containers
"""

# Substrings commonly found in class/id/role attributes for non-content blocks
PARSER_BAD_CONTAINER_HINTS: List[str] = [
    "nav",
    "menu",
    "footer",
    "header",
    "sidebar",
    "side-bar",
    "related",
    "breadcrumb",
    "search",
    "site-tools",
    "utility",
]

# Headings that should be removed because they occur in nav/footers on many sites
PARSER_GENERIC_HEADING_WORDS: Set[str] = {
    "home",
    "search",
    "about",
    "about us",
    "contact",
    "contact us",
    "legal",
    "legal disclaimer",
    "more",
    "resources",
    "help",
}

# Minimum length of a heading to be considered real content
PARSER_MIN_HEADING_LEN: int = 8



# ======================================================================
# ============================ ENRICH CONFIG ============================
# ======================================================================

"""
Configuration used ONLY by enrich.py to:
- Assign topical tags (payments, auto loans, hardship, etc.)
"""

# Main tagging taxonomy for downstream AI workflows
TOPIC_KEYWORDS: Dict[str, List[str]] = {

    # -----------------------------
    # Credit-servicing core topics
    # -----------------------------
    "payments": [
        "payment", "payments", "pay my bill", "due date",
        "autopay", "auto-pay", "automatic payment",
    ],
    "late_fees": [
        "late fee", "late fees", "past due", "delinquent",
        "overdue", "late charge", "late charges",
    ],
    "hardship": [
        "hardship", "forbearance", "payment relief", "relief program",
        "difficulty paying", "cant pay", "can't pay",
    ],
    "disputes": [
        "dispute", "chargeback", "fraudulent", "unauthorized",
        "billing error", "report fraud", "report a charge",
    ],
    "interest": [
        "interest rate", "apr", "annual percentage rate",
        "variable rate", "fixed rate",
    ],
    "fees": [
        "fee", "fees", "annual fee", "balance transfer fee",
        "cash advance fee",
    ],

    # -----------------------------
    # Loan-type categories
    # -----------------------------
    "auto_loans": [
        "auto loan", "car loan", "vehicle loan",
        "auto financing", "car financing", "vehicle financing",
        "auto refinance", "car refinance",
        "down payment", "trade-in", "trade in",
        "dealership financing", "dealer financing",
        "loan-to-value", "ltv",
        "gap insurance", "auto insurance", "vehicle title",
    ],
    "home_loans": [
        "mortgage", "home loan", "housing loan",
        "refinance mortgage", "mortgage refinance",
        "heloc", "home equity", "equity loan",
        "escrow", "property tax", "home insurance",
        "closing costs", "down payment",
        "fixed-rate mortgage", "variable-rate mortgage",
        "conventional loan", "fha loan", "va loan", "jumbo loan",
        "loan-to-value", "ltv",
    ],
    "personal_loans": [
        "personal loan", "installment loan",
        "unsecured loan", "secured loan",
        "origination fee", "fixed monthly payment",
        "credit requirements", "income verification",
        "debt consolidation loan",
    ],
    "student_loans": [
        "student loan", "federal student loan", "private student loan",
        "fafsa", "income-driven repayment", "idr plan",
        "student loan forgiveness", "loan servicer",
        "deferment", "forbearance", "subsidized", "unsubsidized",
        "pell grant", "grace period",
    ],

    # -----------------------------
    # Cross-loan topics
    # -----------------------------
    "refinance": [
        "refinance", "refinancing", "rate and term refinance",
        "cash-out refinance", "lower my rate",
        "lower monthly payment", "refinance options",
    ],
    "debt_consolidation": [
        "consolidate debt", "debt consolidation",
        "balance transfer loan", "merge debts",
        "single payment", "multiple loans",
    ],
    "loan_shopping": [
        "loan shopping", "loan comparison", "compare rates",
        "best rates", "shopping for a loan",
        "soft inquiry", "soft credit check", "hard inquiry",
        "prequalified", "pre-qualification", "preapproved", "pre-approval",
    ],
    "loan_eligibility": [
        "qualify", "eligibility", "credit score required",
        "income requirement", "debt-to-income", "dti",
        "creditworthiness", "underwriting",
    ],
}
