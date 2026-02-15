#!/usr/bin/env python3
"""AI-curated (but deterministic) Catalyst analytics pack.

Goal
----
Publish *lots* of useful leaderboards/trends/flags while keeping everything receipts-first:
- raw dataset: catalyst_proposers_full.json.gz (+ sha256)
- derived artifacts: small CSV/JSON tables for each view

This script is deterministic: no LLM calls. "AI-curated" means we intentionally
choose a menu of views and thresholds that are useful for analysis.

Inputs
------
- data/offchain/catalyst/catalyst_proposers.csv (flattened)
- data/raw/catalyst_proposers_full.json         (full nested scrape)

Outputs (to outputs/offchain/catalyst/analytics/)
-------------------------------------------------
- meta.json
- concentration.json
- leaderboards/*.csv

Notes
-----
- Flags are *signals*, not accusations.
- Dynamic row counts: choose N so the list is informative without being a wall.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def to_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return 0.0


def to_int(x: Any) -> int:
    try:
        return int(float(x))
    except Exception:
        return 0


def money_value(m: Dict[str, Any]) -> Tuple[str, float]:
    code = (m.get('code') or '').strip()
    amt = m.get('amount')
    exp = m.get('exp', 0)
    if amt is None:
        return (code, 0.0)
    try:
        amt_i = int(amt)
        exp_i = int(exp)
        return (code, amt_i / (10 ** exp_i))
    except Exception:
        return (code, 0.0)


def is_ada_code(code: str) -> bool:
    cu = (code or '').upper()
    return 'ADA' in cu


def dynamic_top_n(sorted_values: List[float],
                  min_n: int = 20,
                  max_n: int = 100,
                  cumulative_share_target: float = 0.35) -> int:
    """Pick N so we don't under-show, but also don't dump 500 rows.

    For money leaderboards, pick the smallest N such that top-N captures at least
    cumulative_share_target of the total (clamped to [min_n, max_n]).
    """
    if not sorted_values:
        return min_n
    total = sum(v for v in sorted_values if v and v > 0)
    if total <= 0:
        return min_n
    cum = 0.0
    n = 0
    for v in sorted_values:
        if v <= 0:
            continue
        cum += v
        n += 1
        if n >= min_n and (cum / total) >= cumulative_share_target:
            return min(n, max_n)
        if n >= max_n:
            return max_n
    return max(min_n, min(max_n, n))


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fieldnames})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='data/offchain/catalyst/catalyst_proposers.csv')
    ap.add_argument('--json', default='data/raw/catalyst_proposers_full.json')
    ap.add_argument('--out', default='outputs/offchain/catalyst/analytics')
    args = ap.parse_args()

    inp_csv = Path(args.csv)
    inp_json = Path(args.json)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not inp_csv.exists():
        raise SystemExit(f"Missing {inp_csv}")
    if not inp_json.exists():
        raise SystemExit(f"Missing {inp_json}")

    df = []
    with inp_csv.open('r', encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            df.append(row)

    # Normalize numeric fields
    for r in df:
        for k in ['total_projects','funded_projects','completed_projects']:
            r[k] = to_int(r.get(k))
        for k in ['total_distributed_usd','total_remaining_usd','total_requested_usd',
                  'total_distributed_ada','total_remaining_ada','total_requested_ada']:
            r[k] = to_float(r.get(k))

    # ADA from full JSON (project-level)
    j = json.loads(inp_json.read_text(encoding='utf-8'))
    proposers = j.get('proposers', []) or []

    ada_by_user = defaultdict(float)
    projects_by_user = defaultdict(int)

    for p in proposers:
        user = (p.get('username') or '').strip() or str(p.get('_id') or '')
        for pr in (p.get('projects') or []):
            projects_by_user[user] += 1
            funding = (pr.get('funding') or {})
            dist = funding.get('distributedToDate')
            if isinstance(dist, dict):
                code, val = money_value(dist)
                if is_ada_code(code):
                    ada_by_user[user] += val

    # Build merged rows
    by_user = { (r.get('username') or '').strip(): r for r in df if (r.get('username') or '').strip() }

    merged = []
    for r in df:
        user = (r.get('username') or '').strip()
        r2 = dict(r)
        r2['distributed_ada_from_json'] = round(ada_by_user.get(user, 0.0), 6)
        r2['projects_count_from_json'] = projects_by_user.get(user, 0)
        merged.append(r2)

    # Concentration stats (USD)
    total_usd = sum(r['total_distributed_usd'] for r in merged)
    usd_sorted = sorted((r['total_distributed_usd'] for r in merged), reverse=True)
    def share(topk: int) -> float:
        if total_usd <= 0:
            return 0.0
        return sum(usd_sorted[:topk]) / total_usd

    conc = {
        'total_distributed_usd': total_usd,
        'shares': {
            'top10': share(10),
            'top20': share(20),
            'top50': share(50),
            'top100': share(100),
        }
    }
    (out_dir / 'concentration.json').write_text(json.dumps(conc, indent=2) + '\n', encoding='utf-8')

    # Leaderboards
    leader_dir = out_dir / 'leaderboards'

    def top_rows(key: str, fields: List[str], desc: bool = True, money: bool = False) -> List[Dict[str, Any]]:
        s = sorted(merged, key=lambda r: r.get(key, 0), reverse=desc)
        values = [float(r.get(key, 0) or 0) for r in s]
        if money:
            n = dynamic_top_n(values)
        else:
            n = 50
        return s[:n]

    def emit(name: str, rows: List[Dict[str, Any]], fields: List[str]) -> None:
        write_csv(leader_dir / f'{name}.csv', fields, rows)

    base_fields = ['name','username','total_projects','funded_projects','completed_projects','total_distributed_usd','total_requested_usd','total_remaining_usd','distributed_ada_from_json','catalyst_url']

    emit('top_by_distributed_usd', top_rows('total_distributed_usd', base_fields, True, True), base_fields)
    emit('top_by_requested_usd', top_rows('total_requested_usd', base_fields, True, True), base_fields)
    emit('top_by_total_projects', top_rows('total_projects', base_fields, True, False), base_fields)
    emit('top_by_funded_projects', top_rows('funded_projects', base_fields, True, False), base_fields)
    emit('top_by_completed_projects', top_rows('completed_projects', base_fields, True, False), base_fields)
    emit('top_by_distributed_ada', top_rows('distributed_ada_from_json', base_fields, True, True), base_fields)

    # Flags (signals)
    usd_thr = percentile_threshold = sorted([r['total_distributed_usd'] for r in merged if r['total_distributed_usd'] > 0])
    usd_top1_thr = usd_thr[int(0.99*(len(usd_thr)-1))] if usd_thr else 0.0

    flags = []
    for r in merged:
        funded = int(r.get('funded_projects') or 0)
        completed = int(r.get('completed_projects') or 0)
        dist_usd = float(r.get('total_distributed_usd') or 0.0)
        heavy = dist_usd >= usd_top1_thr and dist_usd > 0
        low_completion = funded >= 5 and (completed / funded) < 0.5
        many_projects = int(r.get('total_projects') or 0) >= 50
        notes = []
        if heavy: notes.append('top_1pct_distributed_usd')
        if low_completion: notes.append('completion_ratio_lt_0.5_funded_ge_5')
        if many_projects: notes.append('high_volume_proposer_ge_50_projects')
        if notes:
            flags.append({
                'username': r.get('username') or '',
                'name': r.get('name') or '',
                'total_projects': r.get('total_projects') or 0,
                'funded_projects': funded,
                'completed_projects': completed,
                'total_distributed_usd': round(dist_usd, 2),
                'distributed_ada_from_json': r.get('distributed_ada_from_json', 0.0),
                'signals': ';'.join(notes),
                'catalyst_url': r.get('catalyst_url') or ''
            })

    flag_fields = ['username','name','signals','total_projects','funded_projects','completed_projects','total_distributed_usd','distributed_ada_from_json','catalyst_url']
    write_csv(out_dir / 'proposer_signals.csv', flag_fields, flags)

    meta = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'curation': {
            'note': 'AI-curated views; deterministic derivation (no LLM). Signals are not accusations.',
            'dynamic_top_n': {
                'min_n': 20,
                'max_n': 100,
                'cumulative_share_target': 0.35,
                'non_money_leaderboards_n': 50,
            }
        },
        'inputs': {
            'csv': str(inp_csv),
            'csv_sha256': sha256_file(inp_csv),
            'json': str(inp_json),
            'json_sha256': sha256_file(inp_json),
        },
        'thresholds': {
            'distributed_usd_top1pct_threshold': usd_top1_thr,
        },
        'counts': {
            'proposers': len(merged),
            'signals_rows': len(flags),
        }
    }
    (out_dir / 'meta.json').write_text(json.dumps(meta, indent=2) + '\n', encoding='utf-8')

    print(f'Wrote {out_dir}')


if __name__ == '__main__':
    main()
