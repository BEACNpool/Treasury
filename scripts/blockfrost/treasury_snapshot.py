#!/usr/bin/env python3
"""Fast "API snapshot" extractor using Blockfrost.

Goal
----
Provide a *clearly-labeled* MAINNET snapshot (tip height/time + key treasury state)
while db-sync is still catching up.

This is NOT a replacement for db-sync (audit-grade). It exists to reduce time-to-first-data
and to provide a second source for cross-checking.

Inputs
------
- BLOCKFROST_PROJECT_ID (required)
- BLOCKFROST_BASE (optional) default: https://cardano-mainnet.blockfrost.io/api/v0

Outputs (written to --out dir)
----------------------------
- status.json   (machine-readable provenance + tip)
- snapshot.csv  (single-row snapshot; intentionally small)

Safety
------
- Refuses to run unless the base URL is clearly *mainnet* (unless --allow-non-mainnet).
- Never writes into docs/outputs directly; publishing is a separate step.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import urllib.request


def http_get_json(url: str, project_id: str, timeout_s: int = 20) -> Any:
    req = urllib.request.Request(url)
    req.add_header("project_id", project_id)
    req.add_header("Accept", "application/json")
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        data = r.read().decode("utf-8")
    return json.loads(data)


def safe_get(url: str, project_id: str) -> Optional[Any]:
    try:
        return http_get_json(url, project_id)
    except Exception:
        return None


def ensure_mainnet_base(base: str, allow_non_mainnet: bool) -> None:
    # Conservative: if user points at preview/preprod, we refuse by default.
    lowered = base.lower()
    looks_mainnet = (
        "mainnet" in lowered
        and "preview" not in lowered
        and "preprod" not in lowered
        and "testnet" not in lowered
    )
    if not looks_mainnet and not allow_non_mainnet:
        raise SystemExit(
            f"Refusing to run: BLOCKFROST_BASE does not look like mainnet: {base!r} (pass --allow-non-mainnet for testing only)"
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Output directory")
    ap.add_argument(
        "--base",
        default=os.getenv("BLOCKFROST_BASE", "https://cardano-mainnet.blockfrost.io/api/v0"),
        help="Blockfrost API base URL (default: cardano-mainnet /api/v0)",
    )
    ap.add_argument(
        "--allow-non-mainnet",
        action="store_true",
        help="Allow non-mainnet base URLs (NEVER publish those outputs).",
    )
    args = ap.parse_args()

    project_id = os.getenv("BLOCKFROST_PROJECT_ID")
    if not project_id:
        raise SystemExit("Missing BLOCKFROST_PROJECT_ID env var")

    ensure_mainnet_base(args.base, args.allow_non_mainnet)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Minimal required probes
    latest_block = http_get_json(f"{args.base}/blocks/latest", project_id)

    # Optional probes (best-effort; endpoints may vary across versions)
    treasury = safe_get(f"{args.base}/treasury", project_id)  # often returns a lovelace string
    epoch_params = safe_get(f"{args.base}/epochs/latest/parameters", project_id)

    generated_at = datetime.now(timezone.utc).isoformat()

    status: Dict[str, Any] = {
        "generated_at_utc": generated_at,
        "source_kind": "blockfrost",
        "network_name": "mainnet",
        "base_url": args.base,
        "tip_block_no": int(latest_block.get("height")) if latest_block and latest_block.get("height") is not None else None,
        "tip_time": (
            datetime.fromtimestamp(int(latest_block["time"]), tz=timezone.utc).isoformat()
            if latest_block and latest_block.get("time") is not None
            else None
        ),
        "notes": "API snapshot (not audit-grade). See methodology; db-sync remains source-of-truth.",
    }

    (out_dir / "status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    # One-row CSV snapshot for quick display/inspection.
    fields = [
        "generated_at_utc",
        "source_kind",
        "network_name",
        "tip_block_no",
        "tip_time",
        "treasury_lovelace",
        "rho",
        "tau",
    ]

    row: Dict[str, Any] = {
        "generated_at_utc": generated_at,
        "source_kind": "blockfrost",
        "network_name": "mainnet",
        "tip_block_no": status["tip_block_no"],
        "tip_time": status["tip_time"],
        "treasury_lovelace": None,
        "rho": None,
        "tau": None,
    }

    # treasury endpoint format varies; handle common shapes.
    if isinstance(treasury, dict) and "treasury" in treasury:
        row["treasury_lovelace"] = treasury.get("treasury")
    elif isinstance(treasury, str):
        row["treasury_lovelace"] = treasury

    if isinstance(epoch_params, dict):
        row["rho"] = epoch_params.get("rho")
        row["tau"] = epoch_params.get("tau")

    out_csv = out_dir / "snapshot.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fields})

    print(f"Wrote {out_dir / 'status.json'}")
    print(f"Wrote {out_csv}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
