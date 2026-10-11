-- Trips, fare and trip time by hour of day, weekday vs weekend
SELECT CASE WHEN d.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
       f.pickup_hour,
       COUNT(*) / COUNT(DISTINCT f.pickup_date)      AS avg_trips_per_day,
       ROUND(AVG(f.fare_amount), 2)                  AS avg_fare,
       ROUND(AVG(f.duration_min), 1)                 AS avg_duration_min
FROM fact_trips f
JOIN dim_date d ON d.date_key = f.pickup_date
GROUP BY 1, 2
ORDER BY 1, 2;
