-- Top 3 pickup zones each day (window function: ROW_NUMBER per day)
WITH daily AS (
    SELECT pickup_date, pu_zone_id, COUNT(*) AS trips
    FROM fact_trips
    GROUP BY 1, 2
), ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY pickup_date ORDER BY trips DESC, pu_zone_id) AS rank_in_day  -- zone id breaks ties so results are deterministic
    FROM daily
)
SELECT r.pickup_date, r.rank_in_day, z.borough, z.zone, r.trips
FROM ranked r
JOIN dim_zone z ON z.zone_id = r.pu_zone_id
WHERE r.rank_in_day <= 3
ORDER BY r.pickup_date, r.rank_in_day;
