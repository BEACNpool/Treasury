#!/usr/bin/env python3
"""Derive publishable Catalyst trends + simple flags from the full scrape.

Inputs:
- data/raw/catalyst_proposers_full.json  (verbatim scrape from projectcatalyst.io)

Outputs (written to outputs/offchain/catalyst/):
- funds.csv              fund-level totals + completion
- proposer_flags.csv     heuristic flags (signals, not accusations)

Notes:
- Off-chain context only.
- Deterministic derivations from the raw scrape.
- Keeps outputs small and publishable.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def money_value(m: Dict[str, Any]) -> Tuple[str, float]:
    """Return (code, value) where value = int(amount)/10^exp."""
    if not isinstance(m, dict):
        return ("", 0.0)
    code = (m.get("code") or "").strip()
    amt = m.get("amount")
    exp = m.get("exp", 0)
    if amt is None:
        return (code, 0.0)
    try:
        amt_i = int(amt)
        exp_i = int(exp)
        return (code, amt_i / (10 ** exp_i))
    except Exception:
        return (code, 0.0)


def add_money(bucket: Dict[str, float], m: Any) -> None:
    # m can be dict or list of dicts
    if isinstance(m, list):
        for x in m:
            add_money(bucket, x)
        return
    if not isinstance(m, dict):
        return
    code, val = money_value(m)
    key = code.upper()
    bucket[key] = bucket.get(key, 0.0) + (val or 0.0)


def percentile_threshold(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(math.floor((pct / 100.0) * (len(s) - 1)))))
    return s[k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", default="data/raw/catalyst_proposers_full.json")
    ap.add_argument("--out", dest="out", default="outputs/offchain/catalyst")
    args = ap.parse_args()

    inp = Path(args.inp)
    if not inp.exists():
        raise SystemExit(f"Missing input: {inp}")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    data = json.loads(inp.read_text(encoding="utf-8"))
    proposers = data.get("proposers", []) or []

    # Fund totals
    fund = defaultdict(lambda: {
        "fund_id": None,
        "projects": 0,
        "proposers": set(),
        "completed_projects": 0,
        "funding": {},
    })

    # Proposer totals
    prop_rows = []
    for p in proposers:
        pid = str(p.get("_id") or "")
        name = p.get("name") or ""
        username = p.get("username") or ""
        funded_projects = int(p.get("fundedProjects") or 0)
        completed_projects = int(p.get("completedProjects") or 0)

        money = {}
        funding = p.get("funding") or {}
        add_money(money, funding.get("totalDistributedToDate"))
        add_money(money, funding.get("totalRemaining"))
        add_money(money, funding.get("totalRequested"))

        prop_rows.append({
            "id": pid,
            "name": name,
            "username": username,
            "funded_projects": funded_projects,
            "completed_projects": completed_projects,
            "distributed_usd": money.get("USD", 0.0),
            "remaining_usd": money.get("USD", 0.0) * 0.0 + money.get("USD_REMAINING", 0.0),
            "requested_usd": money.get("USD_REQUESTED", 0.0),
        })

        # Project-level fund aggregation
        for pr in (p.get("projects") or []):
            fund_id = str(pr.get("fundId") or "")
            if not fund_id:
                continue
            f = fund[fund_id]
            f["fund_id"] = fund_id
            f["projects"] += 1
            f["proposers"].add(username or pid)
            if (pr.get("projectStatus") or "").lower() == "completed" or bool(pr.get("completed")):
                f["completed_projects"] += 1
            pf = pr.get("funding") or {}
            add_money(f["funding"], pf.get("distributedToDate"))
            add_money(f["funding"], pf.get("remaining"))
            add_money(f["funding"], pf.get("requested"))

    # Fix the proposer USD remaining/requested using CSV-derived fields if possible later.
    # Here we only trust the project-level ADA values for fund aggregation.

    # Build funds.csv
    funds_csv = out_dir / "funds.csv"
    fund_fields = [
        "fund_id",
        "projects",
        "proposers",
        "completed_projects",
        "completion_rate",
        "distributed_ada",
        "requested_ada",
        "remaining_ada",
        "distributed_usd",
        "requested_usd",
        "remaining_usd",
    ]

    rows = []
    for fid, f in fund.items():
        funding = f["funding"]
        # Prefer ADA code variants
        ada = 0.0
        req_ada = 0.0
        rem_ada = 0.0
        usd = 0.0
        req_usd = 0.0
        rem_usd = 0.0
        for k, v in funding.items():
            ku = k.upper()
            if "ADA" in ku and "REQUEST" in ku:
                req_ada += v
            elif "ADA" in ku and "REMAIN" in ku:
                rem_ada += v
            elif "ADA" in ku:
                ada += v
            elif ku == "USD":
                usd += v
            elif ku == "USD_REQUESTED":
                req_usd += v
            elif ku == "USD_REMAINING":
                rem_usd += v

        proposers_count = len(f["proposers"])
        projects = int(f["projects"])
        completed = int(f["completed_projects"])
        completion_rate = (completed / projects) if projects else 0.0
        rows.append({
            "fund_id": fid,
            "projects": projects,
            "proposers": proposers_count,
            "completed_projects": completed,
            "completion_rate": round(completion_rate, 3),
            "distributed_ada": round(ada, 6),
            "requested_ada": round(req_ada, 6),
            "remaining_ada": round(rem_ada, 6),
            "distributed_usd": round(usd, 2),
            "requested_usd": round(req_usd, 2),
            "remaining_usd": round(rem_usd, 2),
        })

    rows.sort(key=lambda r: int(r["fund_id"]))
    with funds_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fund_fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Flags (very light)
    # Heavy recipient = top 1% by distributed_usd (from proposer totals)
    dist = [float(r.get("distributed_usd") or 0.0) for r in prop_rows]
    thr = percentile_threshold(dist, 99.0)

    flags_csv = out_dir / "proposer_flags.csv"
    flag_fields = [
        "username",
        "name",
        "funded_projects",
        "completed_projects",
        "distributed_usd",
        "flag_heavy_recipient",
        "flag_low_completion",
        "notes",
    ]

    with flags_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=flag_fields)
        w.writeheader()
        for r in prop_rows:
            funded = int(r.get("funded_projects") or 0)
            completed = int(r.get("completed_projects") or 0)
            distributed_usd = float(r.get("distributed_usd") or 0.0)
            heavy = distributed_usd >= thr and distributed_usd > 0
            low_completion = funded >= 3 and (completed / funded) < 0.5
            notes = []
            if heavy:
                notes.append("top_1pct_by_distributed_usd")
            if low_completion:
                notes.append("completion_ratio_lt_0.5_with_3plus_funded")
            w.writerow({
                "username": r.get("username") or "",
                "name": r.get("name") or "",
                "funded_projects": funded,
                "completed_projects": completed,
                "distributed_usd": round(distributed_usd, 2),
                "flag_heavy_recipient": "1" if heavy else "0",
                "flag_low_completion": "1" if low_completion else "0",
                "notes": ";".join(notes),
            })

    meta = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_url": data.get("metadata", {}).get("source"),
        "scraped_at": data.get("metadata", {}).get("scraped_at"),
        "counts": {
            "proposers": len(proposers),
            "funds": len(rows),
        },
        "heavy_recipient_threshold_usd_top_1pct": thr,
    }
    (out_dir / "derive_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {funds_csv}")
    print(f"Wrote {flags_csv}")
    print(f"Wrote {out_dir / 'derive_meta.json'}")


if __name__ == "__main__":
    main()
