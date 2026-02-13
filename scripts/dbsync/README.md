# Cardano treasury + fee revenue pipeline (db-sync)

This is a minimal, reproducible pipeline to compute (by epoch and by calendar year):

- total transaction fees
- **estimated** treasury inflows sourced from (fees + monetary expansion from reserves)
- treasury outflows via withdrawals (MIR treasury payments pre-Conway; gov-action withdrawals in Conway)
- net treasury change (from `ada_pots` snapshots)

## Prereqs

- A synced `cardano-db-sync` PostgreSQL database (mainnet or preprod).
- Python 3.10+

## Configure DB connection

Set a libpq connection string (recommended):

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/cexplorer'
```

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python treasury_fees.py --dsn "$DATABASE_URL" --out out
```

Outputs:
- `out/epoch_treasury_fees.csv`
- `out/year_treasury_fees.csv`

## Notes

This is intended for analytics/research; it is **not** a ledger-spec reimplementation.
See comments in `treasury_fees.sql` and `treasury_fees.py` for caveats.
