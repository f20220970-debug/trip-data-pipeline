"""Step 5 - Load the warehouse into PostgreSQL and validate it against DuckDB.

* Schema `trips` with dim_zone, dim_date and fact_trips.
* fact_trips is PARTITIONED BY RANGE (pickup_date): one partition per month,
  with foreign keys to the dimensions and indexes created on the parent table
  (Postgres adds them to every partition automatically).
* Idempotent month reload: inside one transaction, drop that month's partition,
  recreate it and bulk-load it with COPY. Re-running a month never duplicates rows,
  and a failure rolls back to the previous data.
* Dimensions are upserted (INSERT ... ON CONFLICT DO UPDATE), so they can be
  refreshed without breaking foreign keys.
* Validation: row counts per month and two analytics queries must give identical
  results in Postgres and DuckDB; any mismatch fails the run.

Connection string comes from the DATABASE_URL environment variable.
"""
import os
import tempfile
from datetime import date
from pathlib import Path

import duckdb
import psycopg

import config as C

PG_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/postgres")

DDL = """
CREATE SCHEMA IF NOT EXISTS trips;
SET search_path TO trips;
CREATE TABLE IF NOT EXISTS dim_zone (
    zone_id INTEGER PRIMARY KEY, borough TEXT, zone TEXT, service_zone TEXT);
CREATE TABLE IF NOT EXISTS dim_date (
    date_key DATE PRIMARY KEY, year INTEGER, month INTEGER, day INTEGER,
    day_of_week INTEGER, day_name TEXT, is_weekend BOOLEAN);
CREATE TABLE IF NOT EXISTS fact_trips (
    pickup_month TEXT NOT NULL,
    pickup_ts TIMESTAMP NOT NULL, dropoff_ts TIMESTAMP NOT NULL,
    pickup_date DATE NOT NULL REFERENCES dim_date (date_key),
    pickup_hour INTEGER NOT NULL,
    pu_zone_id INTEGER NOT NULL REFERENCES dim_zone (zone_id),
    do_zone_id INTEGER NOT NULL REFERENCES dim_zone (zone_id),
    passenger_count DOUBLE PRECISION, trip_distance DOUBLE PRECISION,
    duration_min DOUBLE PRECISION, fare_amount DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION, total_amount DOUBLE PRECISION, payment_type BIGINT
) PARTITION BY RANGE (pickup_date);
CREATE INDEX IF NOT EXISTS ix_fact_pickup_date ON fact_trips (pickup_date);
CREATE INDEX IF NOT EXISTS ix_fact_pu_zone ON fact_trips (pu_zone_id);
"""

FACT_COLS = ("pickup_month, pickup_ts, dropoff_ts, pickup_date, pickup_hour, pu_zone_id, do_zone_id, "
             "passenger_count, trip_distance, duration_min, fare_amount, tip_amount, total_amount, payment_type")

# Queries written in standard SQL, so the same text runs in both databases
CHECKS = {
    "trips_per_month": "SELECT pickup_month, COUNT(*) AS trips FROM fact_trips GROUP BY 1 ORDER BY 1",
    "top_zones_per_day": open(C.SQL_DIR / "02_top_zones_per_day.sql").read().rstrip().rstrip(";"),
    "daily_7d_avg": open(C.SQL_DIR / "03_daily_trips_7d_avg.sql").read().rstrip().rstrip(";"),
}


def month_bounds(month: str):
    y, m = map(int, month.split("-"))
    start = date(y, m, 1)
    end = date(y + (m == 12), m % 12 + 1, 1)
    return start, end


def copy_csv(cur, table: str, cols: str, csv_path: Path) -> None:
    with cur.copy(f"COPY {table} ({cols}) FROM STDIN (FORMAT csv)") as cp, open(csv_path, "rb") as f:
        while data := f.read(1 << 20):
            cp.write(data)


def upsert_dims(cur, duck, tmp: Path) -> None:
    for table, key, cols in [
        ("dim_zone", "zone_id", "zone_id, borough, zone, service_zone"),
        ("dim_date", "date_key", "date_key, year, month, day, day_of_week, day_name, is_weekend"),
    ]:
        csv_path = tmp / f"{table}.csv"
        duck.execute(f"COPY (SELECT {cols} FROM {table}) TO '{csv_path}' (FORMAT csv, HEADER false)")
        cur.execute(f"CREATE TEMP TABLE stg_{table} (LIKE {table}) ON COMMIT DROP")
        copy_csv(cur, f"stg_{table}", cols, csv_path)
        updates = ", ".join(f"{c.strip()} = EXCLUDED.{c.strip()}" for c in cols.split(",")[1:])
        cur.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM stg_{table} "
                    f"ON CONFLICT ({key}) DO UPDATE SET {updates}")


def load_month(pg, duck, month: str, tmp: Path) -> int:
    start, end = month_bounds(month)
    part = f"fact_trips_{month.replace('-', '_')}"
    csv_path = tmp / f"{part}.csv"
    duck.execute(f"COPY (SELECT {FACT_COLS} FROM fact_trips WHERE pickup_month = '{month}') "
                 f"TO '{csv_path}' (FORMAT csv, HEADER false)")
    with pg.transaction():
        with pg.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {part}")
            cur.execute(f"CREATE TABLE {part} PARTITION OF fact_trips "
                        f"FOR VALUES FROM ('{start}') TO ('{end}')")
            copy_csv(cur, part, FACT_COLS, csv_path)
            n = cur.execute(f"SELECT COUNT(*) FROM {part}").fetchone()[0]
    return n


def _normalise(rows) -> list:
    """Make results comparable across databases: dates and numbers as rounded text."""
    out = []
    for r in rows:
        out.append(tuple(f"{float(v):.4f}" if isinstance(v, (int, float)) or hasattr(v, "is_integer") or type(v).__name__ == "Decimal"
                         else str(v)[:10] if hasattr(v, "isoformat") else str(v) for v in r))
    return out


def validate(pg, duck) -> list:
    problems = []
    for name, sql in CHECKS.items():
        d = _normalise(duck.execute(sql).fetchall())
        p = _normalise(pg.execute(sql).fetchall())
        same = d == p
        print(f"  check {name}: {'match' if same else 'MISMATCH'} ({len(d)} rows)")
        if not same:
            problems.append(name)
    return problems


def run(months=None, db_path=None, pg_url=None) -> None:
    months = months or C.MONTHS
    duck = duckdb.connect(str(db_path or C.DB_PATH), read_only=True)
    with psycopg.connect(pg_url or PG_URL, autocommit=True) as pg, tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        pg.execute(DDL)
        pg.execute("SET search_path TO trips")
        print("Postgres")
        with pg.transaction(), pg.cursor() as cur:
            upsert_dims(cur, duck, tmp)
        for m in months:
            n = load_month(pg, duck, m, tmp)
            print(f"  {m}: {n:,} rows loaded into partition fact_trips_{m.replace('-', '_')}")
        problems = validate(pg, duck)
    duck.close()
    if problems:
        raise SystemExit(f"Postgres and DuckDB disagree on: {problems}")
    print("  Postgres matches DuckDB")


if __name__ == "__main__":
    run()
