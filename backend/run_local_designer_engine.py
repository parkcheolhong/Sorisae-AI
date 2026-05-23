from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.marketplace.local_designer_engine import render_local_designer_sequence


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local designer image engine")
    parser.add_argument("--title", default="차 마시는 연속 장면")
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--subtitle-speed", type=float, default=1.0)
    args = parser.parse_args()

    result = render_local_designer_sequence(
        {
            "title": args.title,
            "scenario_script": args.scenario,
            "duration_seconds": args.duration,
            "frames_per_second": args.fps,
            "subtitle_speed": args.subtitle_speed,
        }
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
