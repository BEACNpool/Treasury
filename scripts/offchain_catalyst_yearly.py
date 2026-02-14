#!/usr/bin/env python3
"""Derive a YEARLY off-chain time series from Catalyst project data.

We do *not* publish the full 40MB JSON. We publish derived aggregates.

Method:
- Parse `data/raw/catalyst_proposers_full.json` (scraped from projectcatalyst.io).
- For each project under each proposer:
  - Take `funding.distributedToDate` in USD and/or ADA.
  - Bucket by `updatedAt` year (UTC). This is a proxy timestamp.

Outputs:
- outputs/offchain/catalyst/yearly_distributions.csv

Caveats:
- `updatedAt` is not a perfect payment timestamp.
- Use as OFF-CHAIN analysis context only.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def money_to_float(m: dict) -> float:
    if not m:
        return 0.0
    amt = m.get('amount')
    exp = m.get('exp', 0)
    if amt is None:
        return 0.0
    try:
        amt_i = int(amt)
        exp_i = int(exp)
    except Exception:
        return 0.0
    return amt_i / (10 ** exp_i)


def extract_money_any(obj) -> list[dict]:
    # proposer-level arrays are lists; project-level is single dict.
    if obj is None:
        return []
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        return [obj]
    return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default='data/raw/catalyst_proposers_full.json')
    ap.add_argument('--out', dest='out', default='outputs/offchain/catalyst/yearly_distributions.csv')
    args = ap.parse_args()

    inp = Path(args.inp)
    if not inp.exists():
        raise SystemExit(f"Missing input JSON: {inp}")

    data = json.loads(inp.read_text(encoding='utf-8'))
    proposers = data.get('proposers', [])

    by_year = defaultdict(lambda: {'projects': 0, 'usd': 0.0, 'ada': 0.0})

    for prop in proposers:
        for proj in prop.get('projects', []) or []:
            updated_ms = proj.get('updatedAt')
            if not updated_ms:
                continue
            year = datetime.fromtimestamp(updated_ms / 1000, tz=timezone.utc).year

            funding = proj.get('funding') or {}
            dist = funding.get('distributedToDate')
            for m in extract_money_any(dist):
                code = (m.get('code') or '').upper()
                val = money_to_float(m)
                if code == 'USD':
                    by_year[year]['usd'] += val
                elif 'ADA' in code:
                    by_year[year]['ada'] += val

            by_year[year]['projects'] += 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    years = sorted(by_year.keys())
    with out_path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['year', 'projects', 'distributed_usd', 'distributed_ada'])
        w.writeheader()
        for y in years:
            w.writerow({
                'year': y,
                'projects': by_year[y]['projects'],
                'distributed_usd': round(by_year[y]['usd'], 2),
                'distributed_ada': round(by_year[y]['ada'], 6),
            })

    print(f"Wrote {out_path}")


if __name__ == '__main__':
    main()
