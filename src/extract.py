"""Step 1 - Extract: download the monthly trip files and the zone lookup.

Idempotent: a file that already exists is not downloaded again.
Downloads go to a temporary file first, so a failed download never leaves
a half-written file that later steps would try to read.
"""
import time

import requests

import config as C


def download(url: str, dest, retries: int = 3) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  exists, skipping: {dest.name}")
        return
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            tmp.rename(dest)
            print(f"  downloaded: {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
            return
        except requests.RequestException as e:
            print(f"  attempt {attempt} failed: {e}")
            time.sleep(5 * attempt)
    raise SystemExit(f"Could not download {url}")


def main() -> None:
    C.RAW_DIR.mkdir(parents=True, exist_ok=True)
    print("Extract")
    download(C.ZONE_URL, C.RAW_DIR / "taxi_zone_lookup.csv")
    for month in C.MONTHS:
        download(C.TRIP_URL.format(month=month), C.RAW_DIR / f"yellow_tripdata_{month}.parquet")


if __name__ == "__main__":
    main()
