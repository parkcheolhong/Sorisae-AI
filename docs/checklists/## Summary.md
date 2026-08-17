## Summary

Restores the live frontend runtime path for admin and marketplace flows after recent Next/Turbopack drift.

## Changes

- Unified backend env/proxy resolution and switched the local fallback target to `127.0.0.1:8013`
- Generalized local admin host detection for local webpack/turbopack dev ports
- Restored live Next/Turbopack app-shell config, added admin operational surfaces, and included popup/liveview support updates

## Validation

- `frontend/frontend`: `npm run build` passed
- Backend auth/admin/marketplace requests against `127.0.0.1:8013` succeeded
- Local webpack and turbopack startup reached ready state; remaining interruption was an already-running local dev server on `3005`, not a runtime-config failure
