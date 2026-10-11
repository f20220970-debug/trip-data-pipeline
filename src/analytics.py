"""Step 4 - Run every SQL file in sql/ and export the results to outputs/ as CSV,
then write reports/pipeline_report.md. Your own commentary between the
COMMENTARY markers is kept when the report is regenerated."""
import duckdb
import pandas as pd

import config as C

MARK = "<!-- COMMENTARY -->"


def md(df: pd.DataFrame, n: int = None) -> str:
    df = df.head(n) if n else df
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = ["| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False)]
    return "\n".join([head, sep] + rows)


def kept_commentary(path) -> str:
    default = "_Write 3-5 sentences in your own words: data quality, demand pattern, congestion, one recommendation._"
    if path.exists():
        parts = path.read_text(encoding="utf-8").split(MARK)
        if len(parts) == 3:
            return parts[1].strip()
    return default


def main(db_path=None) -> dict:
    con = duckdb.connect(str(db_path or C.DB_PATH), read_only=True)
    C.OUTPUTS.mkdir(exist_ok=True)
    res = {}
    print("Analytics")
    for sql_file in sorted(C.SQL_DIR.glob("*.sql")):
        name = sql_file.stem[3:]
        df = con.execute(sql_file.read_text()).df()
        df.to_csv(C.OUTPUTS / f"{name}.csv", index=False)
        res[name] = df
        print(f"  {name}: {len(df)} rows")
    load = con.execute("SELECT * FROM load_log WHERE run_at = (SELECT MAX(run_at) FROM load_log) ORDER BY month").df()
    reasons = con.execute("""SELECT source_month AS month, reason, COUNT(*) AS rows
                             FROM quarantine_trips GROUP BY 1, 2 ORDER BY 1, 3 DESC""").df()
    con.close()
    load.to_csv(C.OUTPUTS / "load_summary.csv", index=False)
    write_report(res, load, reasons)
    return res


def write_report(res, load, reasons) -> None:
    out = C.REPORTS / "pipeline_report.md"
    commentary = kept_commentary(out)
    total_in, total_ok = int(load["rows_in"].sum()), int(load["rows_loaded"].sum())
    hour = res["demand_by_hour"]
    wk = hour[hour["day_type"] == "Weekday"]
    peak = wk.loc[wk["avg_trips_per_day"].idxmax()]
    cong = res["peak_congestion"]
    slow = cong.loc[cong["avg_speed_mph"].idxmin()]
    fast = cong.loc[cong["avg_speed_mph"].idxmax()]
    boro = res["borough_fare_time"]
    facts = [
        f"Processed {total_in:,} raw trips; loaded {total_ok:,} ({100 * total_ok / total_in:.2f}%) and quarantined {total_in - total_ok:,}.",
        f"Weekday demand peaks at {int(peak['pickup_hour']):02d}:00 with about {int(peak['avg_trips_per_day']):,} trips per day in that hour.",
        f"Slowest weekday hour: {int(slow['pickup_hour']):02d}:00 at {slow['avg_speed_mph']} mph, versus {fast['avg_speed_mph']} mph at {int(fast['pickup_hour']):02d}:00.",
        f"Busiest pickup borough: {boro.iloc[0]['borough']} ({int(boro.iloc[0]['trips']):,} trips, average fare ${boro.iloc[0]['avg_fare']}).",
    ]
    text = f"""# Trip Data Pipeline Report

## 1. Load summary
{md(load)}

## 2. Data quality
Rows are checked against eight rules. Failed rows go to `quarantine_trips` with the first rule they failed; nothing is silently dropped.

Failures by rule (a row can fail several rules):

{md(res["data_quality_summary"])}

Quarantined rows by reason:

{md(reasons)}

## 3. Key findings
""" + "\n".join(f"- {f}" for f in facts) + f"""

### Analyst commentary
{MARK}
{commentary}
{MARK}

## 4. Monthly totals
{md(res["month_over_month"])}

## 5. Demand by borough
{md(res["borough_fare_time"])}

## 6. Weekday congestion by hour
{md(res["peak_congestion"])}
"""
    C.REPORTS.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"  report: {out.relative_to(C.ROOT)}")


if __name__ == "__main__":
    main()
