-- Treasury + fees research query for cardano-db-sync
--
-- Authoritative sources (ledger-derived, via db-sync):
--   * epoch.fees                 : total transaction fees per epoch
--   * epoch_param.monetary_expand_rate (rho)
--   * epoch_param.treasury_growth_rate (tau)
--   * ada_pots.treasury/reserves : ledger pot balances (snapshot)
--   * treasury                   : MIR payments from treasury (pre-Conway; and still used historically)
--   * pot_transfer               : explicit transfers between reserves/treasury
--   * tx.treasury_donation       : voluntary treasury donations (CIP-??; present in db-sync schema)
--   * gov_action_proposal + treasury_withdrawal: Conway-era treasury withdrawal proposals; enacted_epoch indicates when enacted.
--
-- Output: one row per epoch with both (a) estimated inflows from fees+reserves and (b) observed treasury balance delta.
--
-- IMPORTANT CAVEATS:
--   1) This estimates treasury inflow as tau * (fees + rho * reserves_start).
--      The ledger reward calculation includes additional terms and rounding; and
--      there are effects from refunds, deposits, and unclaimed rewards returning to reserves.
--   2) 'treasury withdrawals' can be measured via:
--        - MIR treasury payments (table treasury) for Shelley->Babbage
--        - Conway enacted treasury withdrawals (gov_action_proposal+treasury_withdrawal)
--      But the most robust outflow measure is: outflows = inflows_other - delta_treasury,
--      after accounting for pot_transfers and treasury_donations.
--

WITH last_pots AS (
  SELECT DISTINCT ON (epoch_no)
    epoch_no,
    slot_no,
    treasury,
    reserves
  FROM ada_pots
  ORDER BY epoch_no, slot_no DESC
),
-- Align each epoch with previous epoch pots so we can compute deltas and use reserves at epoch start.
paired AS (
  SELECT
    e.no AS epoch_no,
    e.start_time,
    e.end_time,
    e.fees AS fees_epoch,
    lp.treasury AS treasury_end,
    lp.reserves  AS reserves_end,
    lpp.treasury AS treasury_start,
    lpp.reserves AS reserves_start
  FROM epoch e
  JOIN last_pots lp   ON lp.epoch_no = e.no
  LEFT JOIN last_pots lpp ON lpp.epoch_no = e.no - 1
),
params AS (
  SELECT
    ep.epoch_no,
    ep.monetary_expand_rate AS rho,
    ep.treasury_growth_rate AS tau
  FROM epoch_param ep
),
mir_treasury_out AS (
  SELECT
    b.epoch_no,
    SUM(t.amount) AS mir_treasury_payments
  FROM treasury t
  JOIN tx     ON tx.id = t.tx_id
  JOIN block b ON b.id = tx.block_id
  GROUP BY b.epoch_no
),
conway_withdrawals AS (
  SELECT
    gap.enacted_epoch AS epoch_no,
    SUM(tw.amount) AS conway_enacted_withdrawals
  FROM gov_action_proposal gap
  JOIN treasury_withdrawal tw ON tw.gov_action_proposal_id = gap.id
  WHERE gap.type = 'TreasuryWithdrawals'
    AND gap.enacted_epoch IS NOT NULL
  GROUP BY gap.enacted_epoch
),
donations AS (
  SELECT
    b.epoch_no,
    SUM(tx.treasury_donation) AS treasury_donations
  FROM tx
  JOIN block b ON b.id = tx.block_id
  GROUP BY b.epoch_no
),
pot_xfers AS (
  SELECT
    b.epoch_no,
    SUM(pt.treasury) AS pot_transfer_treasury
  FROM pot_transfer pt
  JOIN tx     ON tx.id = pt.tx_id
  JOIN block b ON b.id = tx.block_id
  GROUP BY b.epoch_no
)
SELECT
  p.epoch_no,
  p.start_time,
  p.end_time,
  p.fees_epoch,

  p.treasury_start,
  p.treasury_end,
  (p.treasury_end - p.treasury_start) AS treasury_delta,

  p.reserves_start,
  par.rho,
  par.tau,

  -- Monetary expansion approximation: rho * reserves_at_epoch_start
  (par.rho * p.reserves_start)::numeric(30,0) AS monetary_expansion_est,

  -- Treasury inflow from (fees + reserves) approximation: tau * (fees + rho*reserves)
  (par.tau * (p.fees_epoch + (par.rho * p.reserves_start)))::numeric(30,0) AS inflow_fees_plus_reserves_est,

  COALESCE(d.treasury_donations,0) AS treasury_donations,
  COALESCE(px.pot_transfer_treasury,0) AS pot_transfer_treasury,

  COALESCE(mir.mir_treasury_payments,0) AS mir_treasury_payments,
  COALESCE(cw.conway_enacted_withdrawals,0) AS conway_enacted_withdrawals

FROM paired p
LEFT JOIN params par ON par.epoch_no = p.epoch_no
LEFT JOIN mir_treasury_out mir ON mir.epoch_no = p.epoch_no
LEFT JOIN conway_withdrawals cw ON cw.epoch_no = p.epoch_no
LEFT JOIN donations d ON d.epoch_no = p.epoch_no
LEFT JOIN pot_xfers px ON px.epoch_no = p.epoch_no
ORDER BY p.epoch_no;
