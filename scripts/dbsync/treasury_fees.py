#!/usr/bin/env python3
"""Compute Cardano fee revenue + treasury inflows/outflows by epoch and by year.

This script expects a synced cardano-db-sync PostgreSQL schema.

It runs `treasury_fees.sql`, writes epoch-level CSV, then aggregates to calendar year.

Usage:
  python treasury_fees.py --dsn "$DATABASE_URL" --out out

Caveats are documented in the SQL.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import pandas as pd
import psycopg2


def read_sql_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", required=False, default=os.getenv("DATABASE_URL"), help="Postgres DSN")
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument("--sql", required=False, default=str(Path(__file__).with_name("treasury_fees.sql")))
    args = ap.parse_args()

    if not args.dsn:
        raise SystemExit("Missing --dsn (or env DATABASE_URL)")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    sql = read_sql_file(Path(args.sql))

    with psycopg2.connect(args.dsn) as conn:
        df = pd.read_sql_query(sql, conn)

    # Convert Lovelace to ADA convenience columns
    lovelace_cols = [
        "fees_epoch",
        "treasury_start",
        "treasury_end",
        "treasury_delta",
        "reserves_start",
        "monetary_expansion_est",
        "inflow_fees_plus_reserves_est",
        "treasury_donations",
        "pot_transfer_treasury",
        "mir_treasury_payments",
        "conway_enacted_withdrawals",
    ]

    for c in lovelace_cols:
        if c in df.columns:
            df[c + "_ada"] = df[c] / 1e6

    # A simple implied outflow measure: everything that must have left to reconcile delta
    # (Does NOT isolate 'withdrawals' precisely; use the withdrawal columns for that.)
    df["implied_outflow_other_lovelace"] = (
        df["inflow_fees_plus_reserves_est"].fillna(0)
        + df["treasury_donations"].fillna(0)
        + df["pot_transfer_treasury"].fillna(0)
        - df["treasury_delta"].fillna(0)
    )
    df["implied_outflow_other_ada"] = df["implied_outflow_other_lovelace"] / 1e6

    epoch_csv = out_dir / "epoch_treasury_fees.csv"
    df.to_csv(epoch_csv, index=False)

    # Yearly aggregation by epoch start time
    df["year"] = pd.to_datetime(df["start_time"], utc=True).dt.year

    year = (
        df.groupby("year", as_index=False)
        .agg(
            epochs=("epoch_no", "count"),
            fees_ada=("fees_epoch_ada", "sum"),
            inflow_fees_plus_reserves_ada=("inflow_fees_plus_reserves_est_ada", "sum"),
            treasury_delta_ada=("treasury_delta_ada", "sum"),
            mir_treasury_payments_ada=("mir_treasury_payments_ada", "sum"),
            conway_enacted_withdrawals_ada=("conway_enacted_withdrawals_ada", "sum"),
            treasury_donations_ada=("treasury_donations_ada", "sum"),
            pot_transfer_treasury_ada=("pot_transfer_treasury_ada", "sum"),
            implied_outflow_other_ada=("implied_outflow_other_ada", "sum"),
        )
        .sort_values("year")
    )

    year_csv = out_dir / "year_treasury_fees.csv"
    year.to_csv(year_csv, index=False)

    print(f"Wrote {epoch_csv}")
    print(f"Wrote {year_csv}")


if __name__ == "__main__":
    main()
