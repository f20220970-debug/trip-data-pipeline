-- Weekday congestion: average speed by hour, and how slow each hour is versus the fastest hour
WITH hourly AS (
    SELECT f.pickup_hour,
           SUM(f.trip_distance) / (SUM(f.duration_min) / 60.0) AS avg_speed_mph
    FROM fact_trips f
    JOIN dim_date d ON d.date_key = f.pickup_date
    WHERE NOT d.is_weekend
    GROUP BY 1
)
SELECT pickup_hour,
       ROUND(avg_speed_mph, 1) AS avg_speed_mph,
       ROUND(100 * (1 - avg_speed_mph / MAX(avg_speed_mph) OVER ()), 1) AS pct_slower_than_fastest_hour,
       RANK() OVER (ORDER BY avg_speed_mph) AS congestion_rank
FROM hourly
ORDER BY pickup_hour;
