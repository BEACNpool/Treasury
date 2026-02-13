# Data Dictionary

## `outputs/epoch_treasury_fees.csv`

One row per epoch.

Columns (all *lovelace* unless suffixed `_ada`):
- `epoch_no` (int)
- `start_time` (UTC timestamp)
- `end_time` (UTC timestamp)
- `fees_epoch` / `fees_epoch_ada`
- `treasury_start`, `treasury_end`, `treasury_delta` (+ `_ada` versions)
- `reserves_start`
- `rho` (monetary expansion rate)
- `tau` (treasury growth rate)
- `monetary_expansion_est` (+ `_ada`)
- `inflow_fees_plus_reserves_est` (+ `_ada`)
- `treasury_donations` (+ `_ada`)
- `pot_transfer_treasury` (+ `_ada`)
- `mir_treasury_payments` (+ `_ada`)
- `conway_enacted_withdrawals` (+ `_ada`)
- `implied_outflow_other_lovelace` / `implied_outflow_other_ada`

Notes:
- The `_est` columns are **model-based estimates** from protocol parameters and should reconcile (approximately) against `treasury_delta` when combined with explicit transfers/donations.

## `outputs/year_treasury_fees.csv`

Aggregated by calendar year from `start_time`.

Columns:
- `year`
- `epochs`
- `fees_ada`
- `inflow_fees_plus_reserves_ada` (estimate)
- `treasury_delta_ada`
- `mir_treasury_payments_ada`
- `conway_enacted_withdrawals_ada`
- `treasury_donations_ada`
- `pot_transfer_treasury_ada`
- `implied_outflow_other_ada`
