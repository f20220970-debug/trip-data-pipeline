"""Steps 2 and 3 - Data-quality checks, transform and load into DuckDB.

For each month:
  1. Read the raw parquet file into a staging table (only the columns we need).
  2. Flag every row against each data-quality rule.
  3. Clean rows go to the fact table; failed rows go to a quarantine table
     with the first rule they failed. Nothing is silently dropped.
  4. Every rule's failure count is written to dq_log for this run.
The month is deleted and reloaded inside one transaction, so re-running a
month replaces it instead of duplicating it (idempotent), and a failure
half-way leaves the previous load untouched.
"""
import shutil
from datetime import datetime, timezone

import duckdb

import config as C

# Rules in priority order: a row that fails several gets the first as its reason.
RULES = [
    ("missing_required", "pickup_ts IS NULL OR dropoff_ts IS NULL OR pu_zone_id IS NULL "
                         "OR do_zone_id IS NULL OR fare_amount IS NULL OR total_amount IS NULL"),
    ("out_of_month",     "strftime(pickup_ts, '%Y-%m') <> $month"),
    ("pickup_after_dropoff", "dropoff_ts <= pickup_ts"),
    ("too_long",         f"date_diff('second', pickup_ts, dropoff_ts) > {C.MAX_TRIP_HOURS * 3600}"),
    ("zero_distance",    "trip_distance <= 0"),
    ("negative_amount",  "fare_amount < 0 OR total_amount < 0"),
    ("unrealistic_speed", "date_diff('second', pickup_ts, dropoff_ts) > 0 AND "
                          f"trip_distance / (date_diff('second', pickup_ts, dropoff_ts) / 3600.0) > {C.MAX_SPEED_MPH}"),
    ("unknown_zone",     "pu_zone_id NOT IN (SELECT zone_id FROM dim_zone) "
                         "OR do_zone_id NOT IN (SELECT zone_id FROM dim_zone)"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS dim_zone (
    zone_id INTEGER PRIMARY KEY, borough VARCHAR, zone VARCHAR, service_zone VARCHAR);
CREATE TABLE IF NOT EXISTS fact_trips (
    pickup_month VARCHAR, pickup_ts TIMESTAMP, dropoff_ts TIMESTAMP, pickup_date DATE,
    pickup_hour INTEGER, pu_zone_id INTEGER, do_zone_id INTEGER, passenger_count DOUBLE,
    trip_distance DOUBLE, duration_min DOUBLE, fare_amount DOUBLE, tip_amount DOUBLE,
    total_amount DOUBLE, payment_type BIGINT);
CREATE TABLE IF NOT EXISTS quarantine_trips (
    source_month VARCHAR, reason VARCHAR, pickup_ts TIMESTAMP, dropoff_ts TIMESTAMP,
    pu_zone_id INTEGER, do_zone_id INTEGER, passenger_count DOUBLE, trip_distance DOUBLE,
    fare_amount DOUBLE, tip_amount DOUBLE, total_amount DOUBLE, payment_type BIGINT);
CREATE TABLE IF NOT EXISTS dq_log (
    run_at VARCHAR, month VARCHAR, rule VARCHAR, failed_rows BIGINT, total_rows BIGINT, pct_failed DOUBLE);
CREATE TABLE IF NOT EXISTS load_log (
    run_at VARCHAR, month VARCHAR, rows_in BIGINT, rows_loaded BIGINT, rows_quarantined BIGINT);
"""


def load_zones(con, raw_dir) -> None:
    con.execute("DELETE FROM dim_zone")
    con.execute(f"""
        INSERT INTO dim_zone
        SELECT LocationID, Borough, Zone, service_zone
        FROM read_csv_auto('{raw_dir / "taxi_zone_lookup.csv"}', header = true)""")


def load_month(con, month: str, raw_dir, run_at: str) -> dict:
    path = raw_dir / f"yellow_tripdata_{month}.parquet"
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE stg AS
        SELECT CAST(tpep_pickup_datetime AS TIMESTAMP)  AS pickup_ts,
               CAST(tpep_dropoff_datetime AS TIMESTAMP) AS dropoff_ts,
               CAST(PULocationID AS INTEGER) AS pu_zone_id,
               CAST(DOLocationID AS INTEGER) AS do_zone_id,
               CAST(passenger_count AS DOUBLE) AS passenger_count,
               CAST(trip_distance AS DOUBLE)   AS trip_distance,
               CAST(fare_amount AS DOUBLE)     AS fare_amount,
               CAST(tip_amount AS DOUBLE)      AS tip_amount,
               CAST(total_amount AS DOUBLE)    AS total_amount,
               CAST(payment_type AS BIGINT)    AS payment_type
        FROM read_parquet('{path}')""")

    # One boolean column per rule (COALESCE: a NULL comparison counts as not failing that rule;
    # NULLs themselves are caught by missing_required)
    flags = ", ".join(f"COALESCE(({cond}), false) AS f_{name}" for name, cond in RULES)
    reason = "CASE " + " ".join(f"WHEN f_{name} THEN '{name}'" for name, _ in RULES) + " END"
    con.execute(f"CREATE OR REPLACE TEMP TABLE chk AS SELECT *, {flags} FROM stg", {"month": month})
    con.execute(f"CREATE OR REPLACE TEMP TABLE chk2 AS SELECT *, {reason} AS reason FROM chk")

    total = con.execute("SELECT COUNT(*) FROM chk2").fetchone()[0]
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute("DELETE FROM fact_trips WHERE pickup_month = ?", [month])
        con.execute("DELETE FROM quarantine_trips WHERE source_month = ?", [month])
        con.execute("""
            INSERT INTO fact_trips
            SELECT ?, pickup_ts, dropoff_ts, CAST(pickup_ts AS DATE), hour(pickup_ts),
                   pu_zone_id, do_zone_id, passenger_count, trip_distance,
                   date_diff('second', pickup_ts, dropoff_ts) / 60.0,
                   fare_amount, tip_amount, total_amount, payment_type
            FROM chk2 WHERE reason IS NULL""", [month])
        con.execute("""
            INSERT INTO quarantine_trips
            SELECT ?, reason, pickup_ts, dropoff_ts, pu_zone_id, do_zone_id, passenger_count,
                   trip_distance, fare_amount, tip_amount, total_amount, payment_type
            FROM chk2 WHERE reason IS NOT NULL""", [month])
        for name, _ in RULES:
            failed = con.execute(f"SELECT COUNT(*) FROM chk2 WHERE f_{name}").fetchone()[0]
            con.execute("INSERT INTO dq_log VALUES (?, ?, ?, ?, ?, ?)",
                        [run_at, month, name, failed, total, round(100 * failed / total, 4) if total else 0])
        loaded = con.execute("SELECT COUNT(*) FROM fact_trips WHERE pickup_month = ?", [month]).fetchone()[0]
        quarantined = total - loaded
        con.execute("INSERT INTO load_log VALUES (?, ?, ?, ?, ?)", [run_at, month, total, loaded, quarantined])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return {"month": month, "rows_in": total, "loaded": loaded, "quarantined": quarantined}


def build_dim_date(con) -> None:
    con.execute("""
        CREATE OR REPLACE TABLE dim_date AS
        SELECT d::DATE AS date_key, year(d) AS year, month(d) AS month, day(d) AS day,
               dayofweek(d) AS day_of_week, dayname(d) AS day_name,
               dayofweek(d) IN (0, 6) AS is_weekend
        FROM generate_series(
            (SELECT MIN(pickup_date) FROM fact_trips)::TIMESTAMP,
            (SELECT MAX(pickup_date) FROM fact_trips)::TIMESTAMP,
            INTERVAL 1 DAY) AS t(d)""")


def export_partitioned(con, out_dir) -> None:
    """Write the fact table as parquet partitioned by month: data/warehouse/fact_trips/pickup_month=2024-01/..."""
    target = out_dir / "fact_trips"
    if target.exists():
        shutil.rmtree(target)
    out_dir.mkdir(parents=True, exist_ok=True)
    con.execute(f"COPY fact_trips TO '{target}' (FORMAT PARQUET, PARTITION_BY (pickup_month))")


def run(months=None, db_path=None, raw_dir=None, warehouse_dir=None) -> list:
    months = months or C.MONTHS
    db_path, raw_dir = db_path or C.DB_PATH, raw_dir or C.RAW_DIR
    warehouse_dir = warehouse_dir or C.WAREHOUSE_DIR
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA)
    load_zones(con, raw_dir)
    results = []
    print("Load")
    for m in months:
        r = load_month(con, m, raw_dir, run_at)
        print(f"  {m}: {r['rows_in']:,} in -> {r['loaded']:,} loaded, {r['quarantined']:,} quarantined "
              f"({100 * r['quarantined'] / r['rows_in']:.2f}%)")
        results.append(r)
    build_dim_date(con)
    export_partitioned(con, warehouse_dir)
    con.close()
    return results


if __name__ == "__main__":
    run()
