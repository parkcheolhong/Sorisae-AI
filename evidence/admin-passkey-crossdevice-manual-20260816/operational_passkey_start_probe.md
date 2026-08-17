# Operational Passkey Start Probe (2026-08-16)

## Purpose
- verify whether `119cash@naver.com` currently has a registered passkey on production hosts
- detect transient `등록된 패스키가 없습니다` behavior

## Request
- endpoint: `POST /api/auth/passkey/login/start`
- payload: `{"email":"119cash@naver.com"}`

## Result Summary
- host `metanova1004.com`: 3/3 responses were HTTP 200 with `allowCredentials` present
- host `xn--114-2p7l635dz3bh5j.com`: 3/3 responses were HTTP 200 with `allowCredentials` present
- credential id observed: `_TJmgEFKXBvucAzOD24p-EXQd4lCRl4NP_60E3bWeoM`

## Host: metanova1004.com
- round 1: HTTP 200, rpId=`metanova1004.com`, allowCredentials count=1
- round 2: HTTP 200, rpId=`metanova1004.com`, allowCredentials count=1
- round 3: HTTP 200, rpId=`metanova1004.com`, allowCredentials count=1

## Host: xn--114-2p7l635dz3bh5j.com
- round 1: HTTP 200, rpId=`xn--114-2p7l635dz3bh5j.com`, allowCredentials count=1
- round 2: HTTP 200, rpId=`xn--114-2p7l635dz3bh5j.com`, allowCredentials count=1
- round 3: HTTP 200, rpId=`xn--114-2p7l635dz3bh5j.com`, allowCredentials count=1

## Interpretation
- at probe time, server-side lookup did not return `등록된 패스키가 없습니다`
- most likely causes for earlier no-passkey message are:
  1) different environment path (local `localhost` flow vs production domain)
  2) different account/email context at runtime
  3) temporary state drift while registration/login flow was in transition
