#!/usr/bin/env bash
# Runs the PostgreSQL + pgvector memory tests against a throwaway local container.
set -euo pipefail
name=batterymind-pg-test
docker rm -f "$name" >/dev/null 2>&1 || true
docker run -d --name "$name" -e POSTGRES_PASSWORD=test -e POSTGRES_DB=bm -p 54329:5432 pgvector/pgvector:pg16 >/dev/null
trap 'docker rm -f "$name" >/dev/null 2>&1' EXIT
for _ in $(seq 1 40); do docker exec "$name" pg_isready -U postgres >/dev/null 2>&1 && break; sleep 1; done
sleep 2
BATTERYMIND_TEST_PG_URL=postgresql+psycopg://postgres:test@localhost:54329/bm \
  python -m pytest tests/memory/test_postgres.py -q -p no:warnings "$@"
