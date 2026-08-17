# PostgreSQL 19 Beta Compatibility Report (2026-08-09)

## Scope
- Goal: Run PostgreSQL 19 beta in parallel with current PostgreSQL 18.4 for non-disruptive validation.
- Current production-like DB service: `postgres` (`postgres:18.4-alpine`, host port `15432`).
- New test DB service: `postgres19-beta` (`postgres:19beta2-alpine`, host port `15433`, profile `pg19-beta`).

## Compose Changes
- File: `docker-compose.yml`
- Added service: `postgres19-beta`
  - `image: postgres:19beta2-alpine`
  - `profiles: ["pg19-beta"]`
  - `ports: 127.0.0.1:15433:5432`
  - isolated volume: `postgres-data-v19beta`
  - same network and secret mount model as existing postgres service
- Added volume: `postgres-data-v19beta`

## Non-Disruptive Isolation Validation
- `postgres` remained up and healthy while `postgres19-beta` started.
- Version evidence:
  - `postgres` -> `PostgreSQL 18.4 ...`
  - `postgres19-beta` -> `PostgreSQL 19beta2 ...`
- Volume isolation evidence:
  - `postgres` mount: `codeai_postgres-data-v18 -> /var/lib/postgresql`
  - `postgres19-beta` mount: `codeai_postgres-data-v19beta -> /var/lib/postgresql`

## App Connectivity Validation
- Runtime path tested from `devanalysis114-backend` container using SQLAlchemy connection to `postgres19-beta:5432`.
- Query result: `('devanalysis114', 'admin')`
- Result: application driver-level connectivity is confirmed for beta endpoint.

## Migration Compatibility Validation
- Procedure:
  1. Schema-only dump from PostgreSQL 18.4 (`pg_dump --schema-only`).
  2. Restore into PostgreSQL 19 beta test DB (`compat_mig_test`).
- Restore output: DDL statements completed without error signatures.
- Post-restore check:
  - `select count(*) from information_schema.tables where table_schema='public';`
  - Result: `55`
- Result: current schema DDL restore compatibility is confirmed for this snapshot.

## Performance Smoke Comparison (pgbench, same host)
- Method: light TPC-B-like smoke, `-c 4 -j 2 -T 10 -s 3` on each DB.
- PostgreSQL 18.4:
  - TPS: `1820.866678`
  - Avg latency: `2.197 ms`
- PostgreSQL 19beta2:
  - TPS: `1721.105156`
  - Avg latency: `2.324 ms`
- Interpretation:
  - Beta is functional, but this run shows slightly lower TPS/higher latency.
  - This is not a production benchmark; use workload-representative tests before any switch.

## Security Snapshot (Docker Scout Quickview)
- `postgres:18.4-alpine`: `1C / 16H / 18M / 5L`, policy `FAILED (3/7 met)`
- `postgres:19beta2-alpine`: `1C / 16H / 18M / 5L`, policy `FAILED (3/7 met)`
- Shared issues include root user runtime, fixable high/critical vulnerabilities, and missing attestations.

## Decision
- Final recommendation: **Do not switch production to PostgreSQL 19 beta now**.
- Rationale:
  - Beta build is not GA.
  - No security posture improvement vs 18.4 in current snapshot.
  - Smoke performance did not show advantage in this run.
- Recommended path:
  1. Keep production on `postgres:18.4-alpine`.
  2. Keep `postgres19-beta` as parallel validation target under `pg19-beta` profile.
  3. Re-evaluate when PostgreSQL 19 GA image is published and rerun full workload + rollback drill.

## Runbook
- Start beta DB only:
  - `docker compose --profile pg19-beta up -d postgres19-beta`
- Check health:
  - `docker inspect -f "{{.State.Health.Status}}" devanalysis114-postgres19-beta`
- Stop beta DB:
  - `docker compose --profile pg19-beta stop postgres19-beta`
