# Methodology (Draft)

## 1) Definitions

We model treasury as a ledger of flows:

### Inflows
- **Fees → treasury:** portion of transaction fees routed to treasury per protocol.
- **Expansion → treasury:** portion of monetary expansion (reserves) routed to treasury.
- **Other:** deposits/refunds or special cases (explicitly labeled).

### Outflows
- **Treasury withdrawals:** on-chain withdrawals authorized by governance mechanisms (CIP-1694 era) and earlier mechanisms.
- **Program distributions (off-chain):** Catalyst / Intersect grants tracked separately and linked to on-chain withdrawals where possible.

### Balance
- Treasury balance is treated as the ground-truth constraint: cumulative flows should reconcile with observed treasury balance time series.

## 2) Two computation modes

### Mode A — API-derived (fast)
- Uses Koios (or equivalent) endpoints.
- Pros: quick, easy to share.
- Cons: depends on indexer correctness; must be cross-checked.

### Mode B — db-sync / ledger-derived (audit)
- Uses cardano-db-sync SQL.
- Pros: reproducible, verifiable.
- Cons: requires running db-sync or access to a database.

## 3) Reconciliation

We will:
1) Compute per-epoch inflows/outflows.
2) Compute treasury balance time series per epoch.
3) Reconcile: 
   - `balance[t] - balance[t-1] ≈ inflow[t] - outflow[t] (+/- rounding)`
4) Flag any epoch where reconciliation fails beyond tolerance.

## 4) Spending tracking options

We will maintain three parallel indices:

1) **On-chain withdrawals index** (primary)
   - governance action id / tx hash / amount / recipient / epoch.

2) **Program registry index** (secondary)
   - Catalyst funds/projects/milestones/payments.
   - Intersect grants registry.

3) **Unified flow ledger** (analytic)
   - merges rows using evidence links + confidence score.

## 5) Bull market comparisons

We’ll publish yearly aggregates (and optionally monthly):
- fees-to-treasury
- expansion-to-treasury
- withdrawals
- net change

And annotate regime changes (parameter changes, governance era transitions).
