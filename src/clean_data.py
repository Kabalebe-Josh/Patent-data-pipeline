"""
Clean the raw PatentsView TSVs and write tidy CSVs ready for the database.

Output files (in data/clean/):
    clean_patents.csv         (patent_id, title, abstract, filing_date, year)
    clean_inventors.csv       (inventor_id, name, country)
    clean_companies.csv       (company_id, name)
    clean_relationships.csv   (patent_id, inventor_id, company_id)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

import config


def _read_tsv(path: Path, **kwargs) -> pd.DataFrame:
    """Read a TSV with safe defaults for messy patent data."""
    if not path.exists():
        raise FileNotFoundError(
            f"Expected {path} — run `download_data` or `generate_sample_data` first."
        )
    return pd.read_csv(
        path,
        sep="\t",
        dtype=str,            # everything as string; we'll cast explicitly
        keep_default_na=False, # keep blank strings; we want our own NA logic
        na_values=["", "NA", "N/A", "null", "NULL"],
        on_bad_lines="warn",
        encoding="utf-8",
        **kwargs,
    )


def clean_patents() -> pd.DataFrame:
    """patent_id, title, abstract, filing_date, year.

    The brief schema names the date column `filing_date`. PatentsView's
    `g_patent.tsv` only carries `patent_date` (the GRANT date). The actual
    filing date lives in `g_application.tsv`, which we join in here so the
    schema field truly contains a filing date.
    """
    df = _read_tsv(config.RAW_DIR / "g_patent.tsv")

    df = df.rename(columns={
        "patent_title": "title",
        "patent_abstract": "abstract",
    })

    keep = ["patent_id", "title", "abstract", "patent_date"]
    df = df[[c for c in keep if c in df.columns]].copy()

    # Try to attach the real filing_date from g_application.tsv if present.
    app_path = config.RAW_DIR / "g_application.tsv"
    if app_path.exists():
        app = _read_tsv(app_path)
        if {"patent_id", "filing_date"}.issubset(app.columns):
            app = app[["patent_id", "filing_date"]].drop_duplicates(
                subset=["patent_id"], keep="first"
            )
            df = df.merge(app, on="patent_id", how="left")
        else:
            df["filing_date"] = pd.NA
    else:
        df["filing_date"] = pd.NA

    # If we couldn't get a true filing_date, fall back to grant date so the
    # downstream schema field is still populated. Note this in the column.
    if "patent_date" in df.columns:
        df["filing_date"] = df["filing_date"].fillna(df["patent_date"])
        df = df.drop(columns=["patent_date"])

    # Drop rows missing the primary key or the title.
    df = df.dropna(subset=["patent_id", "title"])

    # Trim whitespace on text fields.
    for col in ("title", "abstract"):
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()

    # Parse the date and derive year.
    df["filing_date"] = pd.to_datetime(df["filing_date"], errors="coerce")
    df["year"] = df["filing_date"].dt.year.astype("Int64")

    # Year filter (config.MIN_YEAR / MAX_YEAR).
    if config.MIN_YEAR is not None:
        df = df[(df["year"].isna()) | (df["year"] >= config.MIN_YEAR)]
    if config.MAX_YEAR is not None:
        df = df[(df["year"].isna()) | (df["year"] <= config.MAX_YEAR)]

    # Drop rows whose year is missing once we've applied the filter — those
    # carry no time-series value.
    df = df.dropna(subset=["year"])

    # Dedupe on patent_id (keep first occurrence).
    df = df.drop_duplicates(subset=["patent_id"], keep="first")

    # Format date as ISO string for SQLite friendliness.
    df["filing_date"] = df["filing_date"].dt.strftime("%Y-%m-%d")

    df = df.reset_index(drop=True)
    print(f"[clean]   patents: {len(df):,}")
    return df[["patent_id", "title", "abstract", "filing_date", "year"]]


def clean_locations() -> pd.DataFrame:
    """location_id -> country lookup."""
    df = _read_tsv(config.RAW_DIR / "g_location_disambiguated.tsv")
    df = df.rename(columns={"disambig_country": "country"})
    df = df[["location_id", "country"]].copy()
    df["country"] = df["country"].fillna("").astype(str).str.strip().str.upper()
    df = df.drop_duplicates(subset=["location_id"], keep="first")
    return df


def clean_inventors(valid_patents: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (inventors_df, inventor_relationships_df).

    inventors_df: one row per unique inventor_id with name + country.
    inventor_relationships_df: (patent_id, inventor_id) pairs.
    """
    df = _read_tsv(config.RAW_DIR / "g_inventor_disambiguated.tsv")

    # Field aliases; PatentsView column names changed over time.
    rename = {
        "disambig_inventor_name_first": "first",
        "disambig_inventor_name_last": "last",
        "name_first": "first",
        "name_last": "last",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    needed = ["patent_id", "inventor_id", "first", "last", "location_id"]
    for col in needed:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[needed].copy()

    df = df.dropna(subset=["patent_id", "inventor_id"])

    # Restrict to inventors that link to a patent we kept.
    df = df[df["patent_id"].isin(valid_patents)]

    # Join in country via location.
    locs = clean_locations()
    df = df.merge(locs, on="location_id", how="left")

    # Build full name.
    df["first"] = df["first"].fillna("").astype(str).str.strip()
    df["last"] = df["last"].fillna("").astype(str).str.strip()
    df["name"] = (df["first"] + " " + df["last"]).str.strip()
    df.loc[df["name"] == "", "name"] = "(unknown)"

    # Inventor population: dedupe by inventor_id. If the same inventor appears
    # with multiple countries (rare — usually noise), take the most common.
    inv_country = (
        df[df["country"].notna() & (df["country"] != "")]
        .groupby("inventor_id")["country"]
        .agg(lambda s: s.value_counts().idxmax())
    )
    inv_name = df.groupby("inventor_id")["name"].first()

    inventors = pd.DataFrame({
        "inventor_id": inv_name.index,
        "name": inv_name.values,
    })
    inventors = inventors.merge(
        inv_country.rename("country").reset_index(),
        on="inventor_id",
        how="left",
    )
    inventors["country"] = inventors["country"].fillna("")
    print(f"[clean]   inventors: {len(inventors):,}")

    rel = df[["patent_id", "inventor_id"]].drop_duplicates().reset_index(drop=True)
    return inventors[["inventor_id", "name", "country"]], rel


def clean_companies(valid_patents: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (companies_df, company_relationships_df)."""
    df = _read_tsv(config.RAW_DIR / "g_assignee_disambiguated.tsv")

    rename = {
        "disambig_assignee_organization": "organization",
        "organization": "organization",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    needed = ["patent_id", "assignee_id", "organization"]
    for col in needed:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[needed].copy()
    df = df.rename(columns={"assignee_id": "company_id", "organization": "name"})

    df = df.dropna(subset=["patent_id", "company_id"])

    # Companies only — drop rows where the organization name is missing
    # (those are individual assignees in PatentsView).
    df["name"] = df["name"].fillna("").astype(str).str.strip()
    df = df[df["name"] != ""]

    # Restrict to assignees that link to a patent we kept.
    df = df[df["patent_id"].isin(valid_patents)]

    # Companies population: dedupe by company_id.
    companies = (
        df.groupby("company_id")["name"]
        .first()
        .reset_index()
    )
    print(f"[clean]   companies: {len(companies):,}")

    rel = df[["patent_id", "company_id"]].drop_duplicates().reset_index(drop=True)
    return companies, rel


def build_relationships(
    inv_rel: pd.DataFrame, comp_rel: pd.DataFrame
) -> pd.DataFrame:
    """Outer-join inventor and company relationships per patent.

    Each row links a patent to (inventor_id, company_id). Either side can be
    NULL when a patent has e.g. inventors but no assignee.
    """
    merged = inv_rel.merge(comp_rel, on="patent_id", how="outer")
    merged = merged.drop_duplicates().reset_index(drop=True)
    print(f"[clean]   relationships: {len(merged):,}")
    return merged[["patent_id", "inventor_id", "company_id"]]


def run() -> None:
    config.CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    print("[clean] reading & cleaning ...")

    patents = clean_patents()
    valid_ids: set[str] = set(patents["patent_id"])

    inventors, inv_rel = clean_inventors(valid_ids)
    companies, comp_rel = clean_companies(valid_ids)
    relationships = build_relationships(inv_rel, comp_rel)

    patents.to_csv(config.CLEAN_PATENTS_CSV, index=False)
    inventors.to_csv(config.CLEAN_INVENTORS_CSV, index=False)
    companies.to_csv(config.CLEAN_COMPANIES_CSV, index=False)
    relationships.to_csv(config.CLEAN_RELATIONSHIPS_CSV, index=False)

    print(f"[clean] wrote {config.CLEAN_PATENTS_CSV}")
    print(f"[clean] wrote {config.CLEAN_INVENTORS_CSV}")
    print(f"[clean] wrote {config.CLEAN_COMPANIES_CSV}")
    print(f"[clean] wrote {config.CLEAN_RELATIONSHIPS_CSV}")
    print("[clean] done.")


if __name__ == "__main__":
    try:
        run()
    except FileNotFoundError as e:
        print(f"[clean] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
