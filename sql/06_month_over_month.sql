-- Monthly totals and change vs the previous month (LAG)
SELECT pickup_month,
       COUNT(*)                         AS trips,
       ROUND(SUM(total_amount), 0)      AS gross_revenue,
       ROUND(AVG(fare_amount), 2)       AS avg_fare,
       ROUND(100.0 * (COUNT(*) - LAG(COUNT(*)) OVER (ORDER BY pickup_month))
             / LAG(COUNT(*)) OVER (ORDER BY pickup_month), 1) AS trips_change_pct
FROM fact_trips
GROUP BY 1
ORDER BY 1;
