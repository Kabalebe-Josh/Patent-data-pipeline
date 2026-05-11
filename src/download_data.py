"""
Download real PatentsView granted-patent disambiguated TSVs.

Files are large (multi-GB uncompressed). We stream the zip, extract a single
TSV, and stop early once MAX_ROWS_PER_FILE is reached. This keeps the pipeline
runnable on a laptop.

If the legacy S3 endpoint fails, we retry against the new USPTO ODP location
(post-March-2026 PatentsView migration).
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import requests

import config


def _candidate_urls(filename: str) -> list[str]:
    return [
        f"{config.PATENTSVIEW_S3_BASE}/{filename}",
        f"{config.PATENTSVIEW_ODP_BASE}/{filename}",
    ]


def _download_with_fallback(filename: str) -> bytes:
    """Try each candidate URL in order; return the first successful body."""
    last_err: Exception | None = None
    for url in _candidate_urls(filename):
        try:
            print(f"[download]   GET {url}")
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            buf = io.BytesIO()
            for chunk in r.iter_content(chunk_size=1 << 20):
                if chunk:
                    buf.write(chunk)
            return buf.getvalue()
        except Exception as e:
            print(f"[download]   failed: {e}")
            last_err = e
    raise RuntimeError(f"All sources failed for {filename}") from last_err


def _extract_capped(zip_bytes: bytes, out_path: Path, max_rows: int | None) -> int:
    """Extract the first .tsv member into out_path, stopping after max_rows.

    Returns number of data rows written (excluding header).
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Pick the first TSV inside.
        tsv_name = next(
            (n for n in zf.namelist() if n.lower().endswith(".tsv")),
            None,
        )
        if tsv_name is None:
            raise RuntimeError(f"No .tsv inside the zip; members: {zf.namelist()}")

        with zf.open(tsv_name) as src, out_path.open("wb") as dst:
            # Copy header.
            header = src.readline()
            dst.write(header)
            n = 0
            for line in src:
                dst.write(line)
                n += 1
                if max_rows is not None and n >= max_rows:
                    break
            return n


def download_all() -> None:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[download] saving to {config.RAW_DIR}")
    print(f"[download] MAX_ROWS_PER_FILE = {config.MAX_ROWS_PER_FILE}")

    for logical_name, filename in config.SOURCE_FILES.items():
        out_tsv = config.RAW_DIR / filename.replace(".zip", "")
        if out_tsv.exists():
            print(f"[download] {out_tsv.name} already present, skipping.")
            continue

        print(f"[download] fetching {filename} ...")
        try:
            zip_bytes = _download_with_fallback(filename)
        except Exception as e:
            print(f"[download] ERROR: could not fetch {filename}: {e}",
                  file=sys.stderr)
            print("[download] tip: re-run with --mode sample to use synthetic data",
                  file=sys.stderr)
            raise

        rows = _extract_capped(zip_bytes, out_tsv, config.MAX_ROWS_PER_FILE)
        print(f"[download]   wrote {out_tsv.name}: {rows} rows")

    print("[download] done.")


if __name__ == "__main__":
    download_all()
