"""
Central configuration for the patent pipeline.
All paths, URLs, and tunable knobs live here.
"""
from pathlib import Path

# --- Paths ---------------------------------------------------------------

ROOT = Path(__file__).parent.resolve()
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
REPORTS_DIR = ROOT / "reports"
SQL_DIR = ROOT / "sql"
DB_PATH = ROOT / "patents.db"

# --- Data source URLs ----------------------------------------------------
# PatentsView granted-patent disambiguated tables.
# Legacy S3 mirror is currently the most reliable; the ODP path is the
# post-migration home (March 2026+).

PATENTSVIEW_S3_BASE = "https://s3.amazonaws.com/data.patentsview.org/download"
PATENTSVIEW_ODP_BASE = "https://data.uspto.gov/bulkdata/datasets/pvgpatdis/data"

# Files we need. Keys are logical names; values are the filenames on S3.
# g_application supplies the real filing_date that the brief schema requires
# (g_patent only carries the grant date as patent_date).
SOURCE_FILES = {
    "patent": "g_patent.tsv.zip",
    "application": "g_application.tsv.zip",
    "inventor": "g_inventor_disambiguated.tsv.zip",
    "assignee": "g_assignee_disambiguated.tsv.zip",
    "location": "g_location_disambiguated.tsv.zip",
}

# --- Cleaning / loading knobs --------------------------------------------

# Cap rows per source file during development so the pipeline finishes fast
# and fits in memory. Set to None to load everything.
MAX_ROWS_PER_FILE = 100_000

# Restrict patents to this year range. Keeps the data current and small.
# Set MIN_YEAR = None and MAX_YEAR = None to include all years.
MIN_YEAR = 2018
MAX_YEAR = 2024

# Sample-mode generator: how many patents/inventors/companies to fabricate.
SAMPLE_PATENTS = 5_000
SAMPLE_INVENTORS = 2_000
SAMPLE_COMPANIES = 400

# --- Clean CSV filenames -------------------------------------------------

CLEAN_PATENTS_CSV = CLEAN_DIR / "clean_patents.csv"
CLEAN_INVENTORS_CSV = CLEAN_DIR / "clean_inventors.csv"
CLEAN_COMPANIES_CSV = CLEAN_DIR / "clean_companies.csv"
CLEAN_RELATIONSHIPS_CSV = CLEAN_DIR / "clean_relationships.csv"
