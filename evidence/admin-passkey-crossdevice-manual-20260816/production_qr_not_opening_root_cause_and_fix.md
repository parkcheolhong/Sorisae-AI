# Production QR Not Opening - Root Cause and Fix (2026-08-16)

## User Symptom
- on production admin domain, passkey flow does not open QR sheet

## Root Cause Classification
1. client flow issue (fixed in source)
- forced short timeout could interrupt legitimate WebAuthn QR approval path
- this was removed from admin + marketplace passkey login paths

2. deployment state issue (very likely current blocker)
- user is testing on production domain
- local source edits do not affect production until deployment is completed
- therefore production can still run old bundle behavior until new frontend bundle is deployed

## Source Fix Applied
- removed forced passkey request timeout path from:
  - frontend/frontend/app/admin/login/page.tsx
  - frontend/frontend/app/marketplace/page.tsx
- kept manual cancel action (`처리 중단`) so user can always recover from busy UI state manually
- backend passkey start now includes transport hints for cross-device discovery:
  - transports: hybrid, internal, usb, nfc, ble

## What Must Happen Next
- deploy updated frontend/backend to production
- then re-test on production domain

## Production Re-Verification Checklist (2 rounds)
- [ ] round 1: open production admin login
- [ ] round 1: input `119cash@naver.com`
- [ ] round 1: click passkey login
- [ ] round 1: QR sheet appears
- [ ] round 1: mobile scan + approve
- [ ] round 1: admin dashboard landing success
- [ ] round 1 screenshot saved
- [ ] round 2 repeat all steps and save screenshot

## Pass Criteria
- both rounds show actual QR sheet open and successful dashboard landing

## Fail Criteria
- QR sheet does not open in either round after production deployment
- if failed: collect browser console + network traces for `/api/auth/passkey/login/start` and `/finish`
