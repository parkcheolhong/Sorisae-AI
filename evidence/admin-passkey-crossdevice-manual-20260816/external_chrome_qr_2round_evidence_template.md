# External Chrome QR 2-Round Evidence Template (2026-08-16)

## Status
- round 1: pending user-operated verification
- round 2: pending user-operated verification

## Why pending
- true cross-device QR scan success requires physical phone confirmation on user-owned external Chrome session
- current integrated automation browser cannot act as user phone authenticator

## Preconditions
- target URL: https://xn--114-2p7l635dz3bh5j.com/admin/login
- account email: 119cash@naver.com
- passkey existence precheck: confirmed in `operational_passkey_start_probe.md`

## Round 1 (External Chrome)
- [ ] open login page in external Chrome
- [ ] enter email 119cash@naver.com
- [ ] click passkey login button
- [ ] scan QR with phone and approve
- [ ] verify admin dashboard landing
- [ ] save screenshot: `external-chrome-round1-success.png`
- [ ] record completion time: __________________

## Round 2 (External Chrome)
- [ ] open login page in external Chrome
- [ ] enter email 119cash@naver.com
- [ ] click passkey login button
- [ ] scan QR with phone and approve
- [ ] verify admin dashboard landing
- [ ] save screenshot: `external-chrome-round2-success.png`
- [ ] record completion time: __________________

## Final Gate
- pass condition requires both rounds checked and screenshots present in this folder
- if any round fails, attach browser error text and timestamp in this document
