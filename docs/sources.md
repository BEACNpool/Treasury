# Sources (Draft)

## Primary (preferred)
- Ledger / cardano-db-sync (SQL)

## Secondary (fast iteration)
- Koios endpoints (via BEACN worker if configured)
- Blockfrost API (fast snapshot mode; clearly labeled; not audit-grade)
- Explorer APIs as cross-checks

## Receipts discipline
For every extract, record:
- endpoint/query
- timestamp
- hash of raw response (optional)
- transformation steps
