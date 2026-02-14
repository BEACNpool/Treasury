-- ============================================================================
-- BEACN Treasury — db-sync SQL Queries
-- ============================================================================
-- These queries power the expanded Treasury dashboard.
-- Run against a cardano-db-sync PostgreSQL instance.
-- All amounts stored in lovelace; divided by 1e6 for ADA.
--
-- Repo:  https://github.com/BEACNpool/Treasury
-- Site:  https://beacnpool.github.io/Treasury/
-- ============================================================================


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q1: Reserves + Treasury + Circulating Supply per Epoch                  │
-- │                                                                         │
-- │ The big picture view. Shows all three pools at every epoch boundary.    │
-- │ Circulating = 45B max supply - reserves.                               │
-- │ Output: CSV for the main "Big Picture" chart.                          │
-- └──────────────────────────────────────────────────────────────────────────┘

SELECT
  epoch_no,
  treasury  / 1e6   AS treasury_ada,
  reserves  / 1e6   AS reserves_ada,
  (45e15 - reserves) / 1e6  AS circulating_ada,
  fees      / 1e6   AS fees_ada,
  rewards   / 1e6   AS rewards_ada
FROM ada_pots
ORDER BY epoch_no;


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q2: Treasury Income Per Epoch (Expansion vs. Fees)                     │
-- │                                                                         │
-- │ Uses LAG() to compute per-epoch treasury inflow, then separates the    │
-- │ fee contribution (τ * fees = 20% of fees) from monetary expansion.     │
-- │ Note: "expansion_share" includes any rounding and unclaimed rewards    │
-- │ that flow back, so it's not purely ρ-derived. Treat as approximation.  │
-- └──────────────────────────────────────────────────────────────────────────┘

WITH pots AS (
  SELECT
    epoch_no,
    treasury,
    fees,
    LAG(treasury) OVER (ORDER BY epoch_no) AS prev_treasury,
    LAG(reserves) OVER (ORDER BY epoch_no) AS prev_reserves
  FROM ada_pots
)
SELECT
  epoch_no,
  (treasury - prev_treasury) / 1e6      AS treasury_inflow_ada,
  (fees * 0.2) / 1e6                     AS fee_share_ada,
  ((treasury - prev_treasury) - (fees * 0.2)) / 1e6
                                          AS expansion_share_ada
FROM pots
WHERE prev_treasury IS NOT NULL
ORDER BY epoch_no;


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q3: Yearly Treasury Income Aggregation                                 │
-- │                                                                         │
-- │ Aggregates income by calendar year for the stacked bar chart.          │
-- │ Joins epoch table to get start_time for year extraction.               │
-- └──────────────────────────────────────────────────────────────────────────┘

WITH pots AS (
  SELECT
    epoch_no,
    treasury,
    fees,
    LAG(treasury) OVER (ORDER BY epoch_no) AS prev_treasury
  FROM ada_pots
),
epoch_dates AS (
  SELECT no, EXTRACT(YEAR FROM start_time) AS yr
  FROM epoch
)
SELECT
  ed.yr                                                         AS year,
  SUM((p.fees * 0.2) / 1e6)                                    AS fee_income_ada,
  SUM(((p.treasury - p.prev_treasury) - (p.fees * 0.2)) / 1e6) AS expansion_income_ada,
  SUM((p.treasury - p.prev_treasury) / 1e6)                     AS total_income_ada
FROM pots p
JOIN epoch_dates ed ON ed.no = p.epoch_no
WHERE p.prev_treasury IS NOT NULL
GROUP BY ed.yr
ORDER BY ed.yr;


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q4: Treasury Withdrawals (Conway-era Governance Actions)               │
-- │                                                                         │
-- │ Extracts all enacted treasury withdrawal governance actions.           │
-- │ Shows amounts, destination stake addresses, and enactment epochs.      │
-- │ Requires Conway-era db-sync schema (gov_action_proposal,              │
-- │ treasury_withdrawal tables).                                           │
-- │                                                                         │
-- │ NOTE: Table/column names may vary slightly depending on your           │
-- │ db-sync version. Check with:                                           │
-- │   \dt *treasury*                                                       │
-- │   \dt *gov_action*                                                     │
-- └──────────────────────────────────────────────────────────────────────────┘

SELECT
  b.epoch_no                          AS enacted_epoch,
  tw.amount / 1e6                     AS amount_ada,
  ENCODE(sa.hash_raw, 'hex')          AS stake_address_hash,
  ga.id                               AS gov_action_id,
  ga.type                             AS action_type,
  ENCODE(tx.hash, 'hex')              AS tx_hash
FROM treasury_withdrawal tw
JOIN gov_action_proposal ga   ON ga.id = tw.gov_action_proposal_id
JOIN stake_address sa         ON sa.id = tw.stake_address_id
JOIN tx                       ON tx.id = ga.tx_id
JOIN block b                  ON b.id  = tx.block_id
WHERE ga.type = 'TreasuryWithdrawals'
ORDER BY b.epoch_no DESC, tw.amount DESC;


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q5: NCL Utilization — Cumulative Withdrawals vs. Ceiling               │
-- │                                                                         │
-- │ Running total of treasury withdrawals within the 2025 NCL window       │
-- │ (epochs 532–612). Powers the burn-down progress bar.                   │
-- │                                                                         │
-- │ Adjust epoch range for future NCL periods:                             │
-- │   2025 NCL: epochs 532–612 (extended), ceiling = 350M ADA             │
-- │   2026 NCL: TBD (proposed 350M ADA)                                   │
-- └──────────────────────────────────────────────────────────────────────────┘

WITH withdrawals AS (
  SELECT
    b.epoch_no,
    SUM(tw.amount) / 1e6   AS epoch_withdrawn_ada
  FROM treasury_withdrawal tw
  JOIN gov_action_proposal ga ON ga.id = tw.gov_action_proposal_id
  JOIN tx                     ON tx.id = ga.tx_id
  JOIN block b                ON b.id  = tx.block_id
  WHERE ga.type = 'TreasuryWithdrawals'
    AND b.epoch_no BETWEEN 532 AND 612   -- 2025 NCL window
  GROUP BY b.epoch_no
)
SELECT
  epoch_no,
  epoch_withdrawn_ada,
  SUM(epoch_withdrawn_ada) OVER (
    ORDER BY epoch_no
  ) AS cumulative_withdrawn_ada,
  350000000 - SUM(epoch_withdrawn_ada) OVER (
    ORDER BY epoch_no
  ) AS remaining_headroom_ada
FROM withdrawals
ORDER BY epoch_no;


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q6: Fee Revenue Per Epoch (Transaction Fee Trend)                      │
-- │                                                                         │
-- │ Per-epoch fee totals with a 15-epoch moving average for smoothing.     │
-- │ The long-term sustainability metric: are fees growing fast enough      │
-- │ to replace monetary expansion as reserves deplete?                     │
-- └──────────────────────────────────────────────────────────────────────────┘

SELECT
  epoch_no,
  fees / 1e6              AS total_fees_ada,
  (fees * 0.2) / 1e6     AS treasury_fee_share_ada,
  AVG(fees / 1e6) OVER (
    ORDER BY epoch_no
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) AS fees_15epoch_avg
FROM ada_pots
ORDER BY epoch_no;


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q7: Governance Action Proposal Summary                                 │
-- │                                                                         │
-- │ Lists all governance proposals with amounts for budget categorization. │
-- │ Join with off-chain IPFS metadata for human-readable labels.           │
-- └──────────────────────────────────────────────────────────────────────────┘

SELECT
  ga.id,
  ga.type,
  ga.description,
  b.epoch_no               AS submitted_epoch,
  ga.enacted_epoch,
  ga.ratified_epoch,
  ga.expired_epoch,
  SUM(tw.amount) / 1e6     AS total_amount_ada,
  COUNT(tw.id)              AS withdrawal_count
FROM gov_action_proposal ga
LEFT JOIN treasury_withdrawal tw ON tw.gov_action_proposal_id = ga.id
JOIN tx                          ON tx.id = ga.tx_id
JOIN block b                     ON b.id  = tx.block_id
WHERE ga.type = 'TreasuryWithdrawals'
GROUP BY ga.id, ga.type, ga.description,
         b.epoch_no, ga.enacted_epoch,
         ga.ratified_epoch, ga.expired_epoch
ORDER BY total_amount_ada DESC NULLS LAST;


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q8: Projection Base Data — Current Snapshot                            │
-- │                                                                         │
-- │ Pulls the latest data needed for the sustainability projection model:  │
-- │ current reserves, treasury, avg fees over last year (~73 epochs),      │
-- │ and computed annual income estimates.                                   │
-- │                                                                         │
-- │ Feed these values into a projection script that models:                │
-- │   treasury[y+1] = treasury[y] + expansion_income + fee_income - spend  │
-- │   reserves[y+1] = reserves[y] * (1 - 0.003)^73                        │
-- └──────────────────────────────────────────────────────────────────────────┘

WITH latest AS (
  SELECT * FROM ada_pots
  ORDER BY epoch_no DESC LIMIT 1
),
recent_fees AS (
  SELECT AVG(fees) / 1e6 AS avg_fee_ada
  FROM ada_pots
  WHERE epoch_no >= (SELECT MAX(epoch_no) - 72 FROM ada_pots)
)
SELECT
  l.epoch_no                                AS current_epoch,
  l.treasury  / 1e6                         AS treasury_ada,
  l.reserves  / 1e6                         AS reserves_ada,
  rf.avg_fee_ada                            AS avg_fee_per_epoch_ada,
  rf.avg_fee_ada * 73                       AS est_annual_fee_income_ada,
  (l.reserves * 0.003 * 0.2) / 1e6         AS est_epoch_expansion_to_treasury,
  (l.reserves * 0.003 * 0.2 * 73) / 1e6    AS est_annual_expansion_income_ada
FROM latest l, recent_fees rf;


-- ┌──────────────────────────────────────────────────────────────────────────┐
-- │ Q9: DRep Voting Summary on Treasury Withdrawals                        │
-- │                                                                         │
-- │ BONUS: Shows how DReps voted on each treasury withdrawal proposal.     │
-- │ Useful for governance transparency tooling.                            │
-- └──────────────────────────────────────────────────────────────────────────┘

SELECT
  ga.id                           AS gov_action_id,
  SUBSTRING(ga.description, 1, 80) AS proposal_snippet,
  SUM(tw.amount) / 1e6            AS total_amount_ada,
  COUNT(CASE WHEN v.vote = 'Yes'     THEN 1 END) AS yes_votes,
  COUNT(CASE WHEN v.vote = 'No'      THEN 1 END) AS no_votes,
  COUNT(CASE WHEN v.vote = 'Abstain' THEN 1 END) AS abstain_votes
FROM gov_action_proposal ga
LEFT JOIN treasury_withdrawal tw ON tw.gov_action_proposal_id = ga.id
LEFT JOIN voting_procedure v     ON v.gov_action_proposal_id  = ga.id
WHERE ga.type = 'TreasuryWithdrawals'
GROUP BY ga.id, proposal_snippet
ORDER BY total_amount_ada DESC NULLS LAST;


-- ============================================================================
-- USAGE NOTES
-- ============================================================================
--
-- 1. Export to CSV:
--    psql $DATABASE_URL -c "COPY (<query>) TO STDOUT CSV HEADER" > output.csv
--
-- 2. Conway-era tables (gov_action_proposal, treasury_withdrawal, 
--    voting_procedure) require db-sync 13.3+ with Conway schema.
--    Check your version: SELECT * FROM schema_version ORDER BY id DESC LIMIT 1;
--
-- 3. The τ (tau) = 0.2 and ρ (rho) = 0.003 values are protocol parameters.
--    If governance changes them, update the constants in Q2/Q3/Q8.
--    You can query current params:
--    SELECT min_fee_a, min_fee_b, monetary_expand_rate, treasury_growth_rate
--    FROM epoch_param ORDER BY epoch_no DESC LIMIT 1;
--
-- 4. For the projection model (Q8), the formula per year is:
--    expansion = reserves * (1 - (1-ρ)^73) * τ
--    fee_income = avg_fee_per_epoch * 73 * τ  
--    treasury_next = treasury + expansion + fee_income - annual_spend
--    reserves_next = reserves * (1-ρ)^73
--
-- ============================================================================
