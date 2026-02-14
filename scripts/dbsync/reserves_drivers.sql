-- Reserves drivers (v1): ledger-truth level changes + explicit drivers that are cheap to compute.
--
-- Includes:
-- - reserves_start/reserves_end/reserves_delta (ada_pots snapshots)
-- - pot transfers (pot_transfer.reserves, pot_transfer.treasury)
-- - net deposits/refunds (tx.deposit)
--
-- Excludes for now (too heavy as a naive query): reward table aggregation (rewards by epoch).

WITH last_pots AS (
  SELECT DISTINCT ON (epoch_no)
    epoch_no,
    slot_no,
    treasury,
    reserves
  FROM ada_pots
  ORDER BY epoch_no, slot_no DESC
),
paired AS (
  SELECT
    e.no AS epoch_no,
    e.start_time,
    e.end_time,
    lp.reserves AS reserves_end,
    lpp.reserves AS reserves_start,
    lp.treasury AS treasury_end,
    lpp.treasury AS treasury_start
  FROM epoch e
  JOIN last_pots lp ON lp.epoch_no = e.no
  LEFT JOIN last_pots lpp ON lpp.epoch_no = e.no - 1
),
pot_xfers AS (
  SELECT
    b.epoch_no,
    SUM(pt.reserves) AS pot_transfer_reserves,
    SUM(pt.treasury) AS pot_transfer_treasury
  FROM pot_transfer pt
  JOIN tx ON tx.id = pt.tx_id
  JOIN block b ON b.id = tx.block_id
  GROUP BY b.epoch_no
),
deposits AS (
  SELECT
    b.epoch_no,
    SUM(tx.deposit)::numeric AS deposit_net
  FROM tx
  JOIN block b ON b.id = tx.block_id
  GROUP BY b.epoch_no
)
SELECT
  p.epoch_no,
  p.start_time,
  p.end_time,

  p.reserves_start,
  p.reserves_end,
  (p.reserves_end - p.reserves_start) AS reserves_delta,

  p.treasury_start,
  p.treasury_end,
  (p.treasury_end - p.treasury_start) AS treasury_delta,

  COALESCE(px.pot_transfer_reserves,0) AS pot_transfer_reserves,
  COALESCE(px.pot_transfer_treasury,0) AS pot_transfer_treasury,
  COALESCE(dep.deposit_net,0) AS deposit_net

FROM paired p
LEFT JOIN pot_xfers px ON px.epoch_no = p.epoch_no
LEFT JOIN deposits dep ON dep.epoch_no = p.epoch_no
WHERE p.reserves_start IS NOT NULL
ORDER BY p.epoch_no;
