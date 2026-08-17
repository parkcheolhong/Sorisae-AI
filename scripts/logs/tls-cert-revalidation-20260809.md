# TLS Cert Path Split and Revalidation Evidence (2026-08-09)

## Scope
- Split nginx TLS certificate paths by HTTPS server_name.
- Restart stack with backend readiness gate.
- Revalidate SAN and domain monitoring results.

## Config changes
- File: nginx/nginx.conf/nginx.conf
- Removed shared global cert path from http block.
- Added per-server cert path mapping:
  - 443 server_name localhost xn--114-2p7l635dz3bh5j.com
    - /etc/nginx/local-certs/live/xn--114-2p7l635dz3bh5j.com/fullchain.pem
    - /etc/nginx/local-certs/live/xn--114-2p7l635dz3bh5j.com/privkey.pem
  - 443 server_name metanova1004.com
    - /etc/nginx/local-certs/live/metanova1004.com/fullchain.pem
    - /etc/nginx/local-certs/live/metanova1004.com/privkey.pem
  - 443 server_name api.xn--114-2p7l635dz3bh5j.com
    - /etc/nginx/local-certs/live/xn--114-2p7l635dz3bh5j.com/fullchain.pem
    - /etc/nginx/local-certs/live/xn--114-2p7l635dz3bh5j.com/privkey.pem

## Certificate issuance
- ACME HTTP challenge reachability check: 200 for both domains.
- Issued cert for metanova1004.com:
  - /etc/letsencrypt/live/metanova1004.com/fullchain.pem
  - /etc/letsencrypt/live/metanova1004.com/privkey.pem
- Issued cert for punycode root + api subdomain:
  - /etc/letsencrypt/live/xn--114-2p7l635dz3bh5j.com/fullchain.pem
  - /etc/letsencrypt/live/xn--114-2p7l635dz3bh5j.com/privkey.pem

## Restart execution
- Script: scripts/restart_standard_with_backend_ready.ps1
- Result:
  - backend: healthy
  - frontend-admin: healthy
  - frontend-marketplace: healthy
  - nginx: up

## SAN revalidation (post-restart)
- SNI: metanova1004.com
  - Subject: CN=metanova1004.com
  - SAN: DNS:metanova1004.com
  - Issuer: Let's Encrypt YE2
- SNI: xn--114-2p7l635dz3bh5j.com
  - Subject: CN=xn--114-2p7l635dz3bh5j.com
  - SAN: DNS:xn--114-2p7l635dz3bh5j.com, DNS:api.xn--114-2p7l635dz3bh5j.com
  - Issuer: Let's Encrypt YE1
- SNI: api.xn--114-2p7l635dz3bh5j.com
  - Subject: CN=xn--114-2p7l635dz3bh5j.com
  - SAN: DNS:xn--114-2p7l635dz3bh5j.com, DNS:api.xn--114-2p7l635dz3bh5j.com
  - Issuer: Let's Encrypt YE1

## Domain monitor evidence
- Log file: scripts/logs/domain_status_20260809.log
- Before patch: TLS trust failures recorded as ALERT.
- After patch + cert issuance + restart:
  - xn--114-2p7l635dz3bh5j.com: all checks 200, all passed.
  - metanova1004.com: all checks 200, all passed.

## Conclusion
- Certificate path split is active.
- SAN mappings are correct for both domains and api subdomain.
- Monitoring no longer reports TLS trust chain failures for these domains.
