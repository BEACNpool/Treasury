#!/usr/bin/env python3
"""Build small, publishable indices from Catalyst proposers CSV.

Input:
  data/offchain/catalyst/catalyst_proposers.csv

Outputs:
  outputs/offchain/catalyst/summary.json
  outputs/offchain/catalyst/top_recipients.csv

Notes:
- This is OFF-CHAIN data (Project Catalyst website).
- Used for analysis signals/flags; not guilt.
- We intentionally avoid committing the huge full JSON scrape.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def to_float(x: str) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', default='data/offchain/catalyst/catalyst_proposers.csv')
    ap.add_argument('--out', dest='out', default='outputs/offchain/catalyst')
    ap.add_argument('--top', type=int, default=50)
    args = ap.parse_args()

    inp = Path(args.inp)
    if not inp.exists():
        raise SystemExit(f"Missing input CSV: {inp}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    with inp.open('r', encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)

    total = len(rows)
    funded_any = sum(1 for r in rows if to_float(r.get('funded_projects', '') or '0') > 0)
    completed_any = sum(1 for r in rows if to_float(r.get('completed_projects', '') or '0') > 0)

    dist_usd = sum(to_float(r.get('total_distributed_usd', '') or '0') for r in rows)
    req_usd = sum(to_float(r.get('total_requested_usd', '') or '0') for r in rows)
    rem_usd = sum(to_float(r.get('total_remaining_usd', '') or '0') for r in rows)

    # ADA fields appear as 0 in the current scrape; keep but don’t pretend.
    dist_ada = sum(to_float(r.get('total_distributed_ada', '') or '0') for r in rows)

    top = sorted(rows, key=lambda r: to_float(r.get('total_distributed_usd', '') or '0'), reverse=True)[: args.top]

    top_csv = out_dir / 'top_recipients.csv'
    fields = [
        'id', 'name', 'username', 'catalyst_url',
        'total_projects', 'funded_projects', 'completed_projects',
        'total_distributed_usd', 'total_remaining_usd', 'total_requested_usd',
    ]
    with top_csv.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in top:
            w.writerow({k: r.get(k, '') for k in fields})

    summary = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_kind': 'catalyst',
        'source_url': 'https://projectcatalyst.io/search?type=proposers',
        'input_csv': str(inp),
        'input_sha256': sha256_file(inp),
        'counts': {
            'proposers_total': total,
            'proposers_with_funded_projects': funded_any,
            'proposers_with_completed_projects': completed_any,
        },
        'totals_usd': {
            'distributed_usd': dist_usd,
            'remaining_usd': rem_usd,
            'requested_usd': req_usd,
        },
        'totals_ada': {
            'distributed_ada_reported': dist_ada,
            'note': 'ADA fields in current scrape appear to be 0; use USD totals until verified.',
        },
        'top_recipients_csv': 'top_recipients.csv',
    }

    (out_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')

    print(f"Wrote {top_csv}")
    print(f"Wrote {out_dir / 'summary.json'}")


if __name__ == '__main__':
    main()
