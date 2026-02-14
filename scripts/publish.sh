#!/usr/bin/env bash
# Publish validated mainnet outputs to docs/outputs/ for GitHub Pages.
#
# Usage:
#   bash scripts/publish.sh
#   bash scripts/publish.sh --skip-validate   # skip validation (not recommended)
#
# This script:
#   1) Checks that outputs/status.json exists and says network=mainnet
#   2) Runs validate.py (unless --skip-validate)
#   3) Copies CSVs + status.json into docs/outputs/
#   4) Writes a GENERATED.txt timestamp

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO_ROOT/outputs"
DST="$REPO_ROOT/docs/outputs"

SKIP_VALIDATE=false
if [[ "${1:-}" == "--skip-validate" ]]; then
  SKIP_VALIDATE=true
fi

echo "📦 Publishing outputs → docs/outputs/"
echo "   Source: $SRC"
echo "   Dest:   $DST"

# 1) Check status.json exists
if [[ ! -f "$SRC/status.json" ]]; then
  echo "❌ Missing $SRC/status.json — run the pipeline first."
  exit 1
fi

# 2) Mainnet gate
NETWORK=$(python3 -c "import json; print(json.load(open('$SRC/status.json'))['network_name'])" 2>/dev/null || echo "unknown")
if [[ "$NETWORK" != "mainnet" ]]; then
  echo "❌ status.json says network=$NETWORK — refusing to publish non-mainnet data."
  echo "   Only mainnet outputs should be published to docs/outputs/."
  exit 1
fi
echo "✅ Network: mainnet"

# 3) Validate (unless skipped)
if [[ "$SKIP_VALIDATE" == "false" ]]; then
  echo ""
  echo "🔍 Running validation..."
  python3 "$REPO_ROOT/scripts/validate.py" \
    --epoch "$SRC/epoch_treasury_fees.csv" \
    --year "$SRC/year_treasury_fees.csv"
  echo ""
else
  echo "⚠️  Skipping validation (--skip-validate)"
fi

# 4) Copy files
mkdir -p "$DST"

for f in epoch_treasury_fees.csv year_treasury_fees.csv status.json; do
  if [[ -f "$SRC/$f" ]]; then
    cp "$SRC/$f" "$DST/$f"
    echo "   📄 $f"
  else
    echo "   ⚠️  $f not found, skipping"
  fi
done

# 5) Write timestamp
echo "generated_utc: $(date -u +%Y-%m-%dT%H:%M:%S%z)" > "$DST/GENERATED.txt"

echo ""
echo "✅ Published to $DST"
echo "   Commit and push to update GitHub Pages."
