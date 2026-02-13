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

## Quickstart (coming)

See `docs/methodology.md` and `scripts/`.
