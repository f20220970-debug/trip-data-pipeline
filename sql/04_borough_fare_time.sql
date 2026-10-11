-- Average fare, trip time, distance and card tip rate by pickup borough
SELECT z.borough,
       COUNT(*)                                   AS trips,
       ROUND(AVG(f.fare_amount), 2)               AS avg_fare,
       ROUND(AVG(f.duration_min), 1)              AS avg_duration_min,
       ROUND(AVG(f.trip_distance), 2)             AS avg_distance_miles,
       ROUND(100 * SUM(CASE WHEN f.payment_type = 1 THEN f.tip_amount END)
                 / NULLIF(SUM(CASE WHEN f.payment_type = 1 THEN f.fare_amount END), 0), 1) AS card_tip_pct
FROM fact_trips f
JOIN dim_zone z ON z.zone_id = f.pu_zone_id
GROUP BY 1
ORDER BY trips DESC;
