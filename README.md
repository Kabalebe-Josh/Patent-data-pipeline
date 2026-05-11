# Global Patent Intelligence Data Pipeline

A small data engineering pipeline that collects, cleans, stores, and analyzes
real-world U.S. patent data from the **PatentsView Granted Patent Disambiguated**
dataset.

```
Data Source (PatentsView TSV files)
        │
        ▼
Python download script
        │
        ▼
pandas cleaning  ──►  data/clean/*.csv
        │
        ▼
SQLite database (patents.db)  ◄── sql/schema.sql
        │
        ▼
SQL analysis queries (sql/queries.sql)
        │
        ▼
Reports: console + CSV + JSON
```

## Project structure

```
patent-pipeline/
├── README.md
├── requirements.txt
├── .gitignore
├── main.py                  # one-command orchestrator
├── config.py                # paths, year range, row limits, file URLs
├── src/
│   ├── __init__.py
│   ├── download_data.py     # fetch real PatentsView TSVs (streamed, capped)
│   ├── generate_sample_data.py  # offline fallback for grading without internet
│   ├── clean_data.py        # pandas: dedupe, normalize, fix nulls, derive year
│   ├── load_db.py           # build SQLite schema + load clean CSVs
│   ├── run_queries.py       # execute the seven required SQL queries
│   └── generate_reports.py  # console + CSV + JSON reports
├── sql/
│   ├── schema.sql           # patents, inventors, companies, relationships
│   └── queries.sql          # Q1–Q7 (top-N, trends, JOIN, CTE, window fn)
├── data/
│   ├── raw/                 # downloaded TSVs (gitignored)
│   └── clean/               # clean_*.csv (committed)
└── reports/                 # console.txt, *.csv, report.json (committed)
```

## Setup

Requires Python 3.9+.

```bash
git clone <your-repo-url>
cd patent-pipeline
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the pipeline

Default — downloads the real PatentsView dataset (per the assignment brief):

```bash
python main.py
```

Offline / fast iteration — uses synthetic data with the same shape:

```bash
python main.py --sample
```

You can also run each step individually:

```bash
python -m src.download_data        # or generate_sample_data
python -m src.clean_data
python -m src.load_db
python -m src.run_queries
python -m src.generate_reports
```

## Why SQLite?

The brief requires the project to be reproducible — anyone clones the repo
and runs the code. SQLite ships with Python's standard library, needs no
server, and the whole DB is one file. The schema and queries are vanilla SQL
and will port to Postgres with minor adjustments if needed.

## Data source

Files come from PatentsView's granted-patent disambiguated download:

- Legacy mirror: `https://s3.amazonaws.com/data.patentsview.org/download/`
- New ODP (post-March-2026 migration):
  `https://data.uspto.gov/bulkdata/datasets/pvgpatdis/`

Five files used:

| File | What's in it |
|---|---|
| `g_patent.tsv.zip` | patent_id, title, abstract, grant date |
| `g_application.tsv.zip` | patent_id → **filing_date** (the brief's schema field) |
| `g_inventor_disambiguated.tsv.zip` | inventor_id, name, location_id, patent_id |
| `g_assignee_disambiguated.tsv.zip` | assignee_id, organization, patent_id |
| `g_location_disambiguated.tsv.zip` | location_id, country |

See `PV_grant_data_dictionary.pdf` from PatentsView for full field specs.

## Outputs

After running, `reports/` contains:

- `console.txt` — formatted terminal report (also printed to stdout)
- `top_inventors.csv` — top 10 inventors by patent count
- `top_companies.csv` — top 10 companies by patent count
- `country_trends.csv` — top 10 countries by patent count
- `report.json` — JSON in the exact structure the brief shows
- `yearly_trend.csv`, `q5_join_sample.csv`, `q6_cte_inventor_companies.csv`,
  `q7_window_rank.csv` — the other queries' results, exposed as artifacts

## The seven SQL queries (sql/queries.sql)

| # | What it answers | Technique |
|---|---|---|
| Q1 | Top inventors by patent count | GROUP BY + ORDER BY |
| Q2 | Top companies by patent count | GROUP BY + JOIN |
| Q3 | Top countries producing patents | GROUP BY on inventor country |
| Q4 | Patents per year | GROUP BY year |
| Q5 | Patents combined with inventors and companies | 3-way JOIN |
| Q6 | Top inventors and how many distinct companies they worked with | CTE (WITH) |
| Q7 | Inventors ranked within country and globally | RANK() window function |

## Configuration knobs (`config.py`)

- `MAX_ROWS_PER_FILE` — cap rows per source file. Default 100,000.
  Set to `None` for the full dataset.
- `MIN_YEAR` / `MAX_YEAR` — restrict the patent-year range. Default 2018–2024.
