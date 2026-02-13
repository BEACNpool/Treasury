#!/usr/bin/env python3
"""Build a local DuckDB index from Treasury CSV outputs.

Why DuckDB:
- zero-server
- fast ad-hoc analytics
- easy to publish queries + reproduce results

This script does NOT download data. It only indexes existing CSVs.

Inputs (expected):
- outputs/epoch_treasury_fees.csv
- outputs/year_treasury_fees.csv

Output:
- outputs/treasury.duckdb

Usage:
  python scripts/index_duckdb.py --out outputs/treasury.duckdb
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epoch", default="outputs/epoch_treasury_fees.csv")
    ap.add_argument("--year", default="outputs/year_treasury_fees.csv")
    ap.add_argument("--out", default="outputs/treasury.duckdb")
    args = ap.parse_args()

    epoch = Path(args.epoch)
    year = Path(args.year)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not epoch.exists():
        raise SystemExit(f"missing {epoch}")
    if not year.exists():
        raise SystemExit(f"missing {year}")

    con = duckdb.connect(str(out))

    # Replace tables atomically-ish
    con.execute("DROP TABLE IF EXISTS epoch_treasury")
    con.execute("DROP TABLE IF EXISTS year_treasury")

    con.execute(
        """
        CREATE TABLE epoch_treasury AS
        SELECT * FROM read_csv_auto(?, header=true)
        """,
        [str(epoch)],
    )

    con.execute(
        """
        CREATE TABLE year_treasury AS
        SELECT * FROM read_csv_auto(?, header=true)
        """,
        [str(year)],
    )

    # Convenience views
    con.execute("DROP VIEW IF EXISTS year_overview")
    con.execute(
        """
        CREATE VIEW year_overview AS
        SELECT
          year,
          epochs,
          fees_ada,
          inflow_fees_plus_reserves_ada,
          (mir_treasury_payments_ada + conway_enacted_withdrawals_ada) AS withdrawals_ada,
          treasury_delta_ada,
          implied_outflow_other_ada
        FROM year_treasury
        ORDER BY year;
        """
    )

    # A few basic sanity queries
    rows = con.execute("SELECT COUNT(*) FROM epoch_treasury").fetchone()[0]
    years = con.execute("SELECT COUNT(*) FROM year_treasury").fetchone()[0]

    con.close()
    print(f"indexed epochs={rows} years={years} -> {out}")


if __name__ == "__main__":
    main()
