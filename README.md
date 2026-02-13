# Treasury — Cardano Treasury Inflows/Outflows (Open Research)

Goal: produce an auditable, reproducible view of Cardano treasury **inflows** (fees + expansion + other) and **outflows** (withdrawals / distributions), with multiple levels of rigor:

- **Fast path (API-derived):** Koios / public endpoints for quick iteration.
- **Audit path (ledger/db-sync):** reproducible SQL against cardano-db-sync (gold standard).

This repo is designed to publish:
- clean CSV exports,
- methodology + caveats,
- source receipts.

## Outputs (planned)

- `outputs/epoch_treasury_flows.csv`
- `outputs/year_treasury_flows.csv`
- `outputs/withdrawals_index.csv`
- `docs/methodology.md`

## Principles

- Evidence-first: every computed number traces to a source query + timestamp.
- Prefer on-chain truths over off-chain narratives.
- No secrets committed. API keys/tokens belong in local credential stores.

## Quickstart

### db-sync mode (audit-grade)

1) Export db-sync connection string:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD:5432/DB"
```

2) Run pipeline:

```bash
cd scripts/dbsync
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python treasury_fees.py --dsn "" --out ../../outputs
```

3) Plot yearly chart:

```bash
python ../plot_yearly.py --in ../../outputs/year_treasury_fees.csv --out ../../outputs/year_treasury_fees.png
```

See `docs/data_dictionary.md` for column definitions.

See `docs/methodology.md` for caveats and reconciliation notes.`.
