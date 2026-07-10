import sys
from pathlib import Path

# 패키지 루트(apps/daytrade-ai)를 import 경로에 추가 → `import daytrade` 보장.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
