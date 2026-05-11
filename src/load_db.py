"""
Build the SQLite database from sql/schema.sql and load the clean CSVs.

Idempotent: drops and recreates tables every run.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

import config


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path} — run `clean_data` first.")
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def load() -> None:
    schema_path = config.SQL_DIR / "schema.sql"
    print(f"[load] applying schema {schema_path}")
    with sqlite3.connect(config.DB_PATH) as conn:
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        # Patents.
        patents = _read_csv(config.CLEAN_PATENTS_CSV)
        # Year is integer in the schema.
        if "year" in patents.columns:
            patents["year"] = pd.to_numeric(patents["year"], errors="coerce").astype("Int64")
        patents.to_sql("patents", conn, if_exists="append", index=False)
        print(f"[load]   patents:      {len(patents):>9,}")

        # Inventors.
        inventors = _read_csv(config.CLEAN_INVENTORS_CSV)
        inventors.to_sql("inventors", conn, if_exists="append", index=False)
        print(f"[load]   inventors:    {len(inventors):>9,}")

        # Companies.
        companies = _read_csv(config.CLEAN_COMPANIES_CSV)
        companies.to_sql("companies", conn, if_exists="append", index=False)
        print(f"[load]   companies:    {len(companies):>9,}")

        # Relationships.
        relationships = _read_csv(config.CLEAN_RELATIONSHIPS_CSV)
        relationships.to_sql("relationships", conn, if_exists="append", index=False)
        print(f"[load]   relationships:{len(relationships):>9,}")

        conn.commit()

    print(f"[load] database ready at {config.DB_PATH}")


if __name__ == "__main__":
    try:
        load()
    except FileNotFoundError as e:
        print(f"[load] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
