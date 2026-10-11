"""Tests for the data-quality rules and idempotent loading, on a tiny hand-made month."""
from datetime import datetime

import duckdb
import pandas as pd

import load

ZONES = "LocationID,Borough,Zone,service_zone\n1,Manhattan,Midtown,Yellow Zone\n2,Queens,JFK Airport,Airports\n"


def row(pu, do, dist=2.0, fare=10.0, total=14.0, pu_zone=1, do_zone=2):
    return {"tpep_pickup_datetime": pu, "tpep_dropoff_datetime": do, "passenger_count": 1.0,
            "trip_distance": dist, "PULocationID": pu_zone, "DOLocationID": do_zone,
            "payment_type": 1, "fare_amount": fare, "tip_amount": 2.0, "total_amount": total}


def make_month(tmp_path):
    t = datetime(2024, 1, 10, 9, 0)
    rows = [
        row(t, datetime(2024, 1, 10, 9, 20)),                          # good
        row(t, datetime(2024, 1, 10, 9, 15)),                          # good
        row(t, datetime(2024, 1, 10, 8, 50)),                          # pickup_after_dropoff
        row(t, datetime(2024, 1, 10, 9, 20), dist=0.0),                # zero_distance
        row(t, datetime(2024, 1, 10, 9, 20), fare=-5.0, total=-1.0),   # negative_amount
        row(datetime(2023, 12, 31, 23, 0), datetime(2024, 1, 1, 0, 10)),  # out_of_month
        row(t, datetime(2024, 1, 10, 9, 1), dist=50.0),                # unrealistic_speed (3000 mph)
        row(t, datetime(2024, 1, 10, 9, 20), pu_zone=999),             # unknown_zone
        row(t, datetime(2024, 1, 10, 20, 0)),                          # too_long (11 hours)
    ]
    raw = tmp_path / "raw"
    raw.mkdir()
    pd.DataFrame(rows).to_parquet(raw / "yellow_tripdata_2024-01.parquet")
    (raw / "taxi_zone_lookup.csv").write_text(ZONES)
    return raw


def test_rules_and_idempotency(tmp_path):
    raw = make_month(tmp_path)
    db = tmp_path / "t.duckdb"
    kwargs = dict(months=["2024-01"], db_path=db, raw_dir=raw, warehouse_dir=tmp_path / "wh")

    r1 = load.run(**kwargs)[0]
    assert r1["rows_in"] == 9 and r1["loaded"] == 2 and r1["quarantined"] == 7

    con = duckdb.connect(str(db))
    reasons = set(r[0] for r in con.execute("SELECT reason FROM quarantine_trips").fetchall())
    assert reasons == {"pickup_after_dropoff", "zero_distance", "negative_amount", "out_of_month",
                       "unrealistic_speed", "unknown_zone", "too_long"}
    con.close()

    load.run(**kwargs)   # run the same month again
    con = duckdb.connect(str(db))
    assert con.execute("SELECT COUNT(*) FROM fact_trips").fetchone()[0] == 2        # no duplicates
    assert con.execute("SELECT COUNT(*) FROM quarantine_trips").fetchone()[0] == 7
    con.close()
    assert (tmp_path / "wh" / "fact_trips" / "pickup_month=2024-01").exists()      # partitioned export
