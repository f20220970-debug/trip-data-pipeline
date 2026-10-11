# Trip Data Pipeline Report

## 1. Load summary
| run_at | month | rows_in | rows_loaded | rows_quarantined |
| --- | --- | --- | --- | --- |
| 2026-10-11 09:25 UTC | 2024-01 | 2964624 | 2867218 | 97406 |
| 2026-10-11 09:25 UTC | 2024-02 | 3007526 | 2899200 | 108326 |

## 2. Data quality
Rows are checked against eight rules. Failed rows go to `quarantine_trips` with the first rule they failed; nothing is silently dropped.

Failures by rule (a row can fail several rules):

| month | rule | failed_rows | total_rows | pct_failed |
| --- | --- | --- | --- | --- |
| 2024-01 | zero_distance | 60371 | 2964624 | 2.0364 |
| 2024-01 | negative_amount | 37568 | 2964624 | 1.2672 |
| 2024-01 | too_long | 1772 | 2964624 | 0.0598 |
| 2024-01 | unrealistic_speed | 1024 | 2964624 | 0.0345 |
| 2024-01 | pickup_after_dropoff | 870 | 2964624 | 0.0293 |
| 2024-01 | out_of_month | 18 | 2964624 | 0.0006 |
| 2024-01 | missing_required | 0 | 2964624 | 0.0 |
| 2024-01 | unknown_zone | 0 | 2964624 | 0.0 |
| 2024-02 | zero_distance | 68225 | 3007526 | 2.2685 |
| 2024-02 | negative_amount | 40734 | 3007526 | 1.3544 |
| 2024-02 | too_long | 1736 | 3007526 | 0.0577 |
| 2024-02 | unrealistic_speed | 883 | 3007526 | 0.0294 |
| 2024-02 | pickup_after_dropoff | 803 | 3007526 | 0.0267 |
| 2024-02 | out_of_month | 15 | 3007526 | 0.0005 |
| 2024-02 | missing_required | 0 | 3007526 | 0.0 |
| 2024-02 | unknown_zone | 0 | 3007526 | 0.0 |

Quarantined rows by reason:

| month | reason | rows |
| --- | --- | --- |
| 2024-01 | zero_distance | 59591 |
| 2024-01 | negative_amount | 34138 |
| 2024-01 | too_long | 1772 |
| 2024-01 | unrealistic_speed | 1017 |
| 2024-01 | pickup_after_dropoff | 870 |
| 2024-01 | out_of_month | 18 |
| 2024-02 | zero_distance | 67449 |
| 2024-02 | negative_amount | 37451 |
| 2024-02 | too_long | 1736 |
| 2024-02 | unrealistic_speed | 872 |
| 2024-02 | pickup_after_dropoff | 803 |
| 2024-02 | out_of_month | 15 |

## 3. Key findings
- Processed 5,972,150 raw trips; loaded 5,766,418 (96.56%) and quarantined 205,732.
- Weekday demand peaks at 18:00 with about 7,410 trips per day in that hour.
- Slowest weekday hour: 11:00 at 10.7 mph, versus 22.7 mph at 04:00.
- Busiest pickup borough: Manhattan (5,194,564 trips, average fare $15.06).

### Analyst commentary
<!-- COMMENTARY -->
_Write 3-5 sentences in your own words: data quality, demand pattern, congestion, one recommendation._
<!-- COMMENTARY -->

## 4. Monthly totals
| pickup_month | trips | gross_revenue | avg_fare | trips_change_pct |
| --- | --- | --- | --- | --- |
| 2024-01 | 2867218 | 78375218.0 | 18.49 | nan |
| 2024-02 | 2899200 | 78943450.0 | 18.41 | 1.1 |

## 5. Demand by borough
| borough | trips | avg_fare | avg_duration_min | avg_distance_miles | card_tip_pct |
| --- | --- | --- | --- | --- | --- |
| Manhattan | 5194564 | 15.06 | 13.3 | 2.32 | 23.8 |
| Queens | 493457 | 52.71 | 33.2 | 12.71 | 20.3 |
| Brooklyn | 47014 | 28.42 | 31.9 | 6.07 | 5.8 |
| Unknown | 18526 | 18.93 | 15.0 | 3.35 | 22.6 |
| Bronx | 11563 | 32.91 | 39.3 | 7.93 | 0.7 |
| N/A | 1112 | 68.17 | 23.9 | 8.8 | 14.9 |
| Staten Island | 92 | 38.61 | 21.5 | 9.5 | 21.8 |
| EWR | 90 | 80.97 | 10.2 | 5.03 | 13.3 |

## 6. Weekday congestion by hour
| pickup_hour | avg_speed_mph | pct_slower_than_fastest_hour | congestion_rank |
| --- | --- | --- | --- |
| 0 | 19.3 | 14.9 | 21 |
| 1 | 17.8 | 21.3 | 20 |
| 2 | 17.3 | 23.6 | 19 |
| 3 | 19.4 | 14.2 | 22 |
| 4 | 22.7 | 0.0 | 24 |
| 5 | 22.0 | 2.7 | 23 |
| 6 | 17.0 | 24.9 | 18 |
| 7 | 13.2 | 41.7 | 12 |
| 8 | 11.1 | 50.9 | 5 |
| 9 | 11.1 | 51.2 | 4 |
| 10 | 11.0 | 51.2 | 3 |
| 11 | 10.7 | 52.9 | 1 |
| 12 | 11.2 | 50.7 | 7 |
| 13 | 11.7 | 48.2 | 11 |
| 14 | 11.5 | 49.2 | 10 |
| 15 | 11.1 | 50.8 | 6 |
| 16 | 11.5 | 49.2 | 9 |
| 17 | 10.9 | 51.7 | 2 |
| 18 | 11.4 | 49.9 | 8 |
| 19 | 13.3 | 41.4 | 13 |
| 20 | 14.4 | 36.5 | 14 |
| 21 | 14.7 | 34.9 | 15 |
| 22 | 15.3 | 32.2 | 16 |
| 23 | 16.8 | 25.7 | 17 |
