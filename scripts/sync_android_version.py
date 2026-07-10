#!/usr/bin/env python3
"""Sync app.json version into android/app/build.gradle."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOBILE = ROOT / "apps" / "mobile-nadotongryoksa"
APP_JSON = MOBILE / "app.json"
GRADLE = MOBILE / "android" / "app" / "build.gradle"


def main() -> int:
    app = json.loads(APP_JSON.read_text(encoding="utf-8"))
    vc = int(app["expo"]["android"]["versionCode"])
    vn = str(app["expo"]["version"])
    gradle = GRADLE.read_text(encoding="utf-8")
    gradle = re.sub(r"versionCode\s+\d+", f"versionCode {vc}", gradle)
    gradle = re.sub(r'versionName\s+"[^"]+"', f'versionName "{vn}"', gradle)
    GRADLE.write_text(gradle, encoding="utf-8")
    print(f"[sync] versionCode={vc} versionName={vn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
