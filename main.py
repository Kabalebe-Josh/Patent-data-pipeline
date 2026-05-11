"""
Run the entire patent-intelligence pipeline end-to-end.

  python main.py                # default: real PatentsView data (per brief)
  python main.py --sample       # synthetic data (dev / no-internet fallback)

Steps:
  1. Get raw data (download_data | generate_sample_data)
  2. Clean (clean_data)
  3. Load into SQLite (load_db)
  4. Run queries + generate reports (generate_reports)
"""
from __future__ import annotations

import argparse
import sys
import time

from src import clean_data, generate_reports, generate_sample_data, load_db


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Patent Intelligence Pipeline")
    p.add_argument(
        "--sample",
        action="store_true",
        help="Use synthetic data instead of downloading real PatentsView "
             "files. Useful for offline runs / fast iteration. Default: real.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    t0 = time.time()
    mode = "sample" if args.sample else "real"
    print(f"== mode: {mode} ==\n")

    # Step 1: get raw data
    if args.sample:
        generate_sample_data.generate()
    else:
        # Imported here so the requests dependency isn't needed for sample mode.
        from src import download_data
        download_data.download_all()

    print()

    # Step 2: clean
    clean_data.run()
    print()

    # Step 3: load
    load_db.load()
    print()

    # Step 4: report
    generate_reports.generate()

    print(f"\n== finished in {time.time() - t0:.1f}s ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
