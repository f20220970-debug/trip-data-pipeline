"""All pipeline settings in one place."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
WAREHOUSE_DIR = ROOT / "data" / "warehouse"      # month-partitioned parquet export
DB_PATH = ROOT / "data" / "trips.duckdb"         # DuckDB database (not committed)
OUTPUTS = ROOT / "outputs"                       # small analytics CSVs (committed)
REPORTS = ROOT / "reports"
SQL_DIR = ROOT / "sql"

# Months to process (NYC TLC publishes each month's file about two months later)
MONTHS = ["2024-01", "2024-02"]

# Public NYC Taxi & Limousine Commission data
TRIP_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{month}.parquet"
ZONE_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

# Data-quality thresholds
MAX_TRIP_HOURS = 6        # longer trips are treated as meter errors
MAX_SPEED_MPH = 100       # faster average speeds are impossible in a city
