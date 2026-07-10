#!/usr/bin/env bash
set -euo pipefail

CRON_TAG="SORISAE_UI_API_SMOKE_EVERY_5_MIN"
CURRENT_CRON="$(crontab -l 2>/dev/null || true)"
FILTERED_CRON="$(printf "%s\n" "$CURRENT_CRON" | grep -v "$CRON_TAG" || true)"
printf "%s\n" "$FILTERED_CRON" | crontab -
echo "Removed cron entries tagged with $CRON_TAG"
