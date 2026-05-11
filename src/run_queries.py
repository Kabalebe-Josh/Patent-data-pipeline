"""
Run sql/queries.sql against the SQLite database.

Each query in queries.sql is preceded by `-- @query <name>`. We split on those
markers and execute each block, returning a dict of name -> DataFrame.
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

import config


_QUERY_HEADER = re.compile(r"^\s*--\s*@query\s+(\S+)\s*$", re.MULTILINE)


def parse_queries(sql_text: str) -> list[tuple[str, str]]:
    """Return [(name, sql_block), ...] in order of appearance."""
    matches = list(_QUERY_HEADER.finditer(sql_text))
    if not matches:
        raise ValueError("No `-- @query <name>` markers found in queries.sql")

    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        name = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(sql_text)
        sql_block = sql_text[start:end].strip()
        out.append((name, sql_block))
    return out


def run_all() -> dict[str, pd.DataFrame]:
    queries_path = config.SQL_DIR / "queries.sql"
    if not queries_path.exists():
        raise FileNotFoundError(queries_path)
    if not config.DB_PATH.exists():
        raise FileNotFoundError(
            f"{config.DB_PATH} not found — run `load_db` first."
        )

    sql_text = queries_path.read_text(encoding="utf-8")
    queries = parse_queries(sql_text)

    results: dict[str, pd.DataFrame] = {}
    with sqlite3.connect(config.DB_PATH) as conn:
        for name, sql in queries:
            print(f"[query] running {name} ...")
            df = pd.read_sql_query(sql, conn)
            results[name] = df
            print(f"[query]   rows: {len(df)}")
    return results


def main() -> None:
    results = run_all()
    print()
    for name, df in results.items():
        print(f"=== {name} ===")
        print(df.head(10).to_string(index=False))
        print()


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as e:
        print(f"[query] ERROR: {e}", file=sys.stderr)
        sys.exit(1)
