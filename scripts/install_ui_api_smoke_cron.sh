#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SMOKE_SCRIPT="$SCRIPT_DIR/run_ui_api_failure_split_smoke.ps1"
CRON_TAG="# SORISAE_UI_API_SMOKE_EVERY_5_MIN"

if [[ ! -f "$SMOKE_SCRIPT" ]]; then
  echo "Smoke script not found: $SMOKE_SCRIPT" >&2
  exit 1
fi

if command -v pwsh >/dev/null 2>&1; then
  PS_BIN="pwsh"
elif command -v powershell >/dev/null 2>&1; then
  PS_BIN="powershell"
else
  echo "Neither pwsh nor powershell is available on PATH" >&2
  exit 2
fi

LOG_PATH="$SCRIPT_DIR/ui_api_smoke_cron.log"
CRON_LINE="*/5 * * * * cd \"$REPO_ROOT\" && $PS_BIN -NoProfile -ExecutionPolicy Bypass -File \"$SMOKE_SCRIPT\" >> \"$LOG_PATH\" 2>&1 $CRON_TAG"

CURRENT_CRON="$(crontab -l 2>/dev/null || true)"
FILTERED_CRON="$(printf "%s\n" "$CURRENT_CRON" | grep -v "SORISAE_UI_API_SMOKE_EVERY_5_MIN" || true)"

{
  printf "%s\n" "$FILTERED_CRON"
  printf "%s\n" "$CRON_LINE"
} | sed '/^$/N;/^\n$/D' | crontab -

echo "Installed cron entry:"
echo "$CRON_LINE"
