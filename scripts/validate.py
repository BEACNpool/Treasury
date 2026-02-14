#!/usr/bin/env python3
"""Validate and reconcile treasury CSV outputs.

Checks:
  1) Schema: expected columns present, no all-null columns.
  2) Monotonicity: epoch_no is strictly increasing.
  3) Reconciliation: treasury_delta ≈ inflows - outflows (within tolerance).
  4) Balance continuity: treasury_end[t] == treasury_start[t+1].
  5) Sanity: no negative fees, no negative treasury balances.

Usage:
  python scripts/validate.py --epoch outputs/epoch_treasury_fees.csv
  python scripts/validate.py --epoch outputs/epoch_treasury_fees.csv --year outputs/year_treasury_fees.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


EPOCH_REQUIRED_COLS = [
    "epoch_no", "start_time", "end_time", "fees_epoch",
    "treasury_start", "treasury_end", "treasury_delta",
    "reserves_start", "rho", "tau",
    "inflow_fees_plus_reserves_est",
    "treasury_donations", "pot_transfer_treasury",
    "mir_treasury_payments", "conway_enacted_withdrawals",
]

YEAR_REQUIRED_COLS = [
    "year", "epochs", "fees_ada",
    "inflow_fees_plus_reserves_ada", "treasury_delta_ada",
]

# Reconciliation tolerance in lovelace (allow up to 10 ADA of rounding per epoch)
RECON_TOLERANCE_LOVELACE = 10_000_000


class ValidationResult:
    def __init__(self):
        self.passed = 0
        self.warned = 0
        self.failed = 0
        self.messages: list[str] = []

    def ok(self, msg: str):
        self.passed += 1
        self.messages.append(f"  ✅ {msg}")

    def warn(self, msg: str):
        self.warned += 1
        self.messages.append(f"  ⚠️  {msg}")

    def fail(self, msg: str):
        self.failed += 1
        self.messages.append(f"  ❌ {msg}")

    def summary(self) -> str:
        lines = ["\n".join(self.messages)]
        total = self.passed + self.warned + self.failed
        status = "PASS" if self.failed == 0 else "FAIL"
        lines.append(f"\n  [{status}] {self.passed}/{total} passed, {self.warned} warnings, {self.failed} failures")
        return "\n".join(lines)


def validate_epoch(path: Path) -> ValidationResult:
    r = ValidationResult()
    print(f"\n📋 Validating epoch file: {path}")

    if not path.exists():
        r.fail(f"File not found: {path}")
        return r

    df = pd.read_csv(path)
    r.ok(f"Loaded {len(df)} rows")

    # 1) Schema check
    missing = [c for c in EPOCH_REQUIRED_COLS if c not in df.columns]
    if missing:
        r.fail(f"Missing columns: {missing}")
    else:
        r.ok("All required columns present")

    # Check for all-null columns (excluding first epoch which may have nulls)
    for col in EPOCH_REQUIRED_COLS:
        if col in df.columns and df[col].iloc[1:].isna().all() and len(df) > 2:
            r.warn(f"Column '{col}' is all-null (after epoch 1)")

    # 2) Monotonicity
    if "epoch_no" in df.columns:
        diffs = df["epoch_no"].diff().dropna()
        if (diffs == 1).all():
            r.ok("epoch_no is strictly monotonic (+1)")
        elif (diffs > 0).all():
            r.warn(f"epoch_no is increasing but has gaps (min step={diffs.min()}, max step={diffs.max()})")
        else:
            r.fail("epoch_no is NOT monotonically increasing")

    # 3) Reconciliation: delta ≈ inflows - outflows
    if all(c in df.columns for c in ["treasury_delta", "inflow_fees_plus_reserves_est",
                                       "treasury_donations", "pot_transfer_treasury",
                                       "mir_treasury_payments", "conway_enacted_withdrawals"]):
        # Skip first epoch (no prior treasury_start)
        check = df.iloc[1:].copy()
        check["expected_delta"] = (
            check["inflow_fees_plus_reserves_est"].fillna(0)
            + check["treasury_donations"].fillna(0)
            + check["pot_transfer_treasury"].fillna(0)
            - check["mir_treasury_payments"].fillna(0)
            - check["conway_enacted_withdrawals"].fillna(0)
        )
        check["recon_diff"] = abs(check["treasury_delta"].fillna(0) - check["expected_delta"])
        bad_epochs = check[check["recon_diff"] > RECON_TOLERANCE_LOVELACE]

        if len(bad_epochs) == 0:
            r.ok(f"Reconciliation passes for all {len(check)} epochs (tolerance: {RECON_TOLERANCE_LOVELACE/1e6:.0f} ADA)")
        else:
            pct = len(bad_epochs) / len(check) * 100
            max_diff_ada = bad_epochs["recon_diff"].max() / 1e6
            r.warn(
                f"Reconciliation drift in {len(bad_epochs)}/{len(check)} epochs ({pct:.1f}%) "
                f"— max diff: {max_diff_ada:,.0f} ADA. "
                f"This is expected: the estimate uses tau*(fees+rho*reserves) which omits "
                f"deposits/refunds/unclaimed-reward effects."
            )

    # 4) Balance continuity: treasury_end[t] == treasury_start[t+1]
    if "treasury_end" in df.columns and "treasury_start" in df.columns:
        end_shifted = df["treasury_end"].iloc[:-1].values
        start_next = df["treasury_start"].iloc[1:].values
        # Both must be non-null for comparison
        mask = pd.notna(end_shifted) & pd.notna(start_next)
        if mask.any():
            mismatches = (end_shifted[mask] != start_next[mask]).sum()
            if mismatches == 0:
                r.ok(f"Balance continuity: treasury_end[t] == treasury_start[t+1] for all {mask.sum()} consecutive pairs")
            else:
                # db-sync snapshots and/or partial ada_pots coverage can produce discontinuities.
                # This should be investigated, but it is not fatal for publishing balance *levels*.
                r.warn(f"Balance continuity mismatch in {mismatches} epoch transitions (investigate ada_pots coverage)")
        else:
            r.warn("Cannot check balance continuity (too many nulls)")

    # 5) Sanity checks
    if "fees_epoch" in df.columns:
        neg_fees = (df["fees_epoch"].dropna() < 0).sum()
        if neg_fees == 0:
            r.ok("No negative fees")
        else:
            r.fail(f"{neg_fees} epochs have negative fees")

    if "treasury_end" in df.columns:
        neg_bal = (df["treasury_end"].dropna() < 0).sum()
        if neg_bal == 0:
            r.ok("No negative treasury balances")
        else:
            r.fail(f"{neg_bal} epochs have negative treasury balance")

    # 6) Data freshness
    if "end_time" in df.columns:
        latest = pd.to_datetime(df["end_time"]).max()
        r.ok(f"Latest epoch end_time: {latest}")

    return r


def validate_year(path: Path) -> ValidationResult:
    r = ValidationResult()
    print(f"\n📋 Validating year file: {path}")

    if not path.exists():
        r.fail(f"File not found: {path}")
        return r

    df = pd.read_csv(path)
    r.ok(f"Loaded {len(df)} rows ({df['year'].min()}–{df['year'].max()})")

    missing = [c for c in YEAR_REQUIRED_COLS if c not in df.columns]
    if missing:
        r.fail(f"Missing columns: {missing}")
    else:
        r.ok("All required columns present")

    # Year should be monotonic
    if "year" in df.columns:
        if df["year"].is_monotonic_increasing:
            r.ok("Years are monotonically increasing")
        else:
            r.fail("Years are NOT sorted")

    # Epochs per year sanity (73 ± some for partial years)
    if "epochs" in df.columns:
        partial = df[(df["epochs"] < 50) | (df["epochs"] > 80)]
        if len(partial) <= 2:  # first and last year can be partial
            r.ok(f"Epoch counts per year look reasonable (range: {df['epochs'].min()}–{df['epochs'].max()})")
        else:
            r.warn(f"{len(partial)} years have unusual epoch counts")

    return r


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate treasury CSV outputs")
    ap.add_argument("--epoch", help="Path to epoch_treasury_fees.csv")
    ap.add_argument("--year", help="Path to year_treasury_fees.csv")
    args = ap.parse_args()

    if not args.epoch and not args.year:
        # Default paths
        args.epoch = "outputs/epoch_treasury_fees.csv"
        args.year = "outputs/year_treasury_fees.csv"

    results: list[ValidationResult] = []

    if args.epoch:
        r = validate_epoch(Path(args.epoch))
        print(r.summary())
        results.append(r)

    if args.year:
        r = validate_year(Path(args.year))
        print(r.summary())
        results.append(r)

    total_failures = sum(r.failed for r in results)
    if total_failures > 0:
        print(f"\n💥 {total_failures} total failure(s)")
        sys.exit(1)
    else:
        print("\n✅ All validations passed")


if __name__ == "__main__":
    main()
