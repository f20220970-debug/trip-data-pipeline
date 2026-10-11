-- Failures by rule for the latest run (a row can fail several rules)
SELECT month, rule, failed_rows, total_rows, pct_failed
FROM dq_log
WHERE run_at = (SELECT MAX(run_at) FROM dq_log)
ORDER BY month, failed_rows DESC;
