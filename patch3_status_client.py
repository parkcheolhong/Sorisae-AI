"""Patch 3: Add env-variable constants to trading_system status_client.py template (line 566)."""
import re

filepath = "backend/llm/orchestrator.py"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Target line 566 (0-indexed: 565)
# The block starts at line 566 with:
#   "backend/app/external_adapters/status_client.py": (
#       "from __future__ import annotations\n"
#       "import time\n"
#       "import httpx\n\n"
#       "def build_provider_status_map() -> list[dict]:\n"
# We need to insert "import os\n" line and 3 constant lines after "import httpx\n\n"

target_line = 565  # 0-indexed (line 566 in file)

# Verify it is the right line
if 'status_client.py": (' not in lines[target_line]:
    raise ValueError(f"Unexpected content at line {target_line+1}: {lines[target_line]}")

# Find "import time\n" and "import httpx\n\n" within next 10 lines
import_time_idx = None
import_httpx_idx = None
for i in range(target_line, target_line + 10):
    if '"import time\\n"' in lines[i]:
        import_time_idx = i
    if '"import httpx\\n\\n"' in lines[i]:
        import_httpx_idx = i

print(f"import time at line {import_time_idx+1 if import_time_idx else 'NOT FOUND'}")
print(f"import httpx at line {import_httpx_idx+1 if import_httpx_idx else 'NOT FOUND'}")

if import_time_idx is None or import_httpx_idx is None:
    # Print the lines around target for inspection
    for i in range(target_line, target_line + 12):
        print(f"  L{i+1}: {lines[i].rstrip()}")
    raise ValueError("Could not find expected import lines")

# Insert "import os\n" before "import time\n"
os_import_line = '            "import os\\n"\n'
lines.insert(import_time_idx, os_import_line)
# After insert, import_httpx_idx shifts by 1
import_httpx_idx += 1

# Insert 3 constant lines after "import httpx\n\n"
# Find the new position of import httpx line
const_lines = [
    '            "UPSTREAM_STATUS_BASE_URL = os.getenv(\'UPSTREAM_STATUS_BASE_URL\', \'https://broker.example.com\')\\n"\n',
    '            "NOTIFICATION_GATEWAY_URL = os.getenv(\'NOTIFICATION_GATEWAY_URL\', \'https://notify.example.com\')\\n"\n',
    '            "REQUEST_TIMEOUT_SEC = float(os.getenv(\'REQUEST_TIMEOUT_SEC\', \'5\'))\\n\\n"\n',
]

# Insert after import_httpx line (after \n\n terminator)
insert_pos = import_httpx_idx + 1
for j, cl in enumerate(const_lines):
    lines.insert(insert_pos + j, cl)

# But we need to remove the \n\n from the existing import httpx line and replace it with just \n
# Actually the httpx line currently has \n\n which serves as the blank line
# We want: import httpx\n (just newline), then blank line AFTER constants
# Let's check what the current httpx line looks like
print(f"httpx line ({import_httpx_idx+1}): {lines[import_httpx_idx].rstrip()}")

# The current content has "import httpx\n\n" meaning it provides the blank line
# After inserting constants, the order will be:
# "import httpx\n\n"
# constants...
# "def build_provider_status_map...
# We want:
# "import httpx\n"
# constants (last one has \n\n)
# "def build_provider_status_map...
# Modify the httpx line to remove extra \n
lines[import_httpx_idx] = lines[import_httpx_idx].replace('"import httpx\\n\\n"', '"import httpx\\n"')
print(f"httpx line after fix ({import_httpx_idx+1}): {lines[import_httpx_idx].rstrip()}")

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Patch 3 applied successfully!")

# Verify
with open(filepath, "r", encoding="utf-8") as f:
    verlines = f.readlines()
for i in range(target_line, target_line + 12):
    print(f"  L{i+1}: {verlines[i].rstrip()}")
