-- Daily trips with a 7-day moving average and day-on-day change (window functions)
WITH daily AS (
    SELECT pickup_date, COUNT(*) AS trips
    FROM fact_trips
    GROUP BY 1
)
SELECT pickup_date, trips,
       ROUND(AVG(trips) OVER (ORDER BY pickup_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 0) AS trips_7d_avg,
       trips - LAG(trips) OVER (ORDER BY pickup_date) AS change_vs_prev_day
FROM daily
ORDER BY pickup_date;
