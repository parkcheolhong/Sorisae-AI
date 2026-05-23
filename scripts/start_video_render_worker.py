from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.marketplace.router import run_ad_order_worker


if __name__ == "__main__":
    run_ad_order_worker()