# Admin Docs Nginx Next Route Checklist

## Status Rules

- Implemented: config was changed but deployment or live verification is still open.
- Completed: config was changed, redeployed, and the three required URLs passed two live verification runs.
- Failed: nginx still routes `/docs` away from the Next admin app or any required live verification fails.

## Checklist

- [x] 1. Confirm the active nginx `/docs` rule is the controlling route.
- [x] 2. Change `/docs` to proxy to `frontend_admin` so the Next app owns the route.
- [x] 3. Redeploy nginx with the updated mounted config.
- [x] 4. Run the same three production URLs twice and capture status and redirect evidence.
- [x] 5. Synchronize final evidence and close this checklist only after both runs pass.

## Target Files

- nginx/nginx.conf/nginx.conf
- docs/checklists/admin-docs-nginx-next-route-checklist.md

## Planned Verification

- Syntax check: `docker compose exec -T nginx nginx -t`
- Reload: `docker compose up -d nginx`
- Live verification run 1:
  - `https://xn--114-2p7l635dz3bh5j.com/admin/docs-viewer?path=docs%2Fidentity-provider-integration-contract.md`
  - `https://xn--114-2p7l635dz3bh5j.com/admin/docs-viewer?path=docs%2Fidentity-provider-commercial-terms-checklist.md`
  - `https://xn--114-2p7l635dz3bh5j.com/docs`
- Live verification run 2:
  - `https://xn--114-2p7l635dz3bh5j.com/admin/docs-viewer?path=docs%2Fidentity-provider-integration-contract.md`
  - `https://xn--114-2p7l635dz3bh5j.com/admin/docs-viewer?path=docs%2Fidentity-provider-commercial-terms-checklist.md`
  - `https://xn--114-2p7l635dz3bh5j.com/docs`

## Evidence Log

- Status: Completed
- Control hypothesis: the `location ^~ /docs` block in nginx is the highest-priority rule for `/docs`, so switching its upstream changes the production behavior without touching app code.
- Syntax check:
  - `docker compose exec -T nginx nginx -t`
  - Result: syntax ok, configuration test successful.
- Active config evidence:
  - `docker compose exec -T nginx sh -lc "nginx -T 2>/dev/null | sed -n '400,408p'"`
  - Result: `location ^~ /docs {` now shows `proxy_pass http://frontend_admin;`.
- Redeploy:
  - `docker compose up -d nginx`
  - Result: `devanalysis114-nginx` remained `Up` after reload.
- Supporting parity check:
  - `http://127.0.0.1:3005/docs` -> `307 Location=/admin`
- Live verification run 1:
  - `200 | https://xn--114-2p7l635dz3bh5j.com/admin/docs-viewer?path=docs%2Fidentity-provider-integration-contract.md | Location=`
  - `200 | https://xn--114-2p7l635dz3bh5j.com/admin/docs-viewer?path=docs%2Fidentity-provider-commercial-terms-checklist.md | Location=`
  - `307 | https://xn--114-2p7l635dz3bh5j.com/docs | Location=/admin`
- Live verification run 2:
  - `200 | https://xn--114-2p7l635dz3bh5j.com/admin/docs-viewer?path=docs%2Fidentity-provider-integration-contract.md | Location=`
  - `200 | https://xn--114-2p7l635dz3bh5j.com/admin/docs-viewer?path=docs%2Fidentity-provider-commercial-terms-checklist.md | Location=`
  - `307 | https://xn--114-2p7l635dz3bh5j.com/docs | Location=/admin`

## Final Status

- Result: Completed
