-- Fee income time series (on-chain) from db-sync.
-- Uses epoch.fees (per-epoch total tx fees) and computes a cumulative sum.

SELECT
  e.no AS epoch_no,
  e.start_time,
  e.fees AS fees_epoch_lovelace,
  (e.fees / 1e6) AS fees_epoch_ada,
  SUM(e.fees) OVER (ORDER BY e.no) AS cumulative_fees_lovelace,
  (SUM(e.fees) OVER (ORDER BY e.no) / 1e6) AS cumulative_fees_ada
FROM epoch e
WHERE e.fees IS NOT NULL
ORDER BY e.no;
