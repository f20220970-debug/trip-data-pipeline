"""Run the whole pipeline: extract -> data-quality checks + load -> analytics + report."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import analytics  # noqa: E402
import extract    # noqa: E402
import load       # noqa: E402

if __name__ == "__main__":
    t0 = time.time()
    extract.main()
    load.run()
    analytics.main()
    print(f"Pipeline finished in {time.time() - t0:.0f}s")
