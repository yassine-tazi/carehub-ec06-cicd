#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/02_conteneurisation"
if [ ! -f .env.dev ]; then
  PW="LocalDemo-$(date +%s)-$RANDOM"
  cat > .env.dev <<ENV
APP_ENV=development
APP_PORT=8080
APP_IMAGE=carehub-app:local
APP_REPLICAS=1
POSTGRES_DB=carehub
POSTGRES_USER=carehub
POSTGRES_PASSWORD=$PW
VCS_REF=local-demo
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ENV
fi

echo '=== [1] Build + start ==='
docker compose --env-file .env.dev up -d --build
for i in $(seq 1 30); do curl -fsS http://localhost:8080/ready && break || sleep 2; done

echo '=== [2] CAPTURE - containers ==='
docker compose --env-file .env.dev ps

echo '=== [3] CAPTURE - health ==='
curl -fsS http://localhost:8080/health; echo
curl -fsS http://localhost:8080/ready; echo

echo '=== [4] CAPTURE - appointment ==='
curl -fsS -X POST http://localhost:8080/api/appointments -H 'Content-Type: application/json' -d '{"patient_reference":"PATIENT-DEMO-001","requested_at":"2026-09-18T10:00:00Z","specialty":"Cardiologie"}'; echo

echo '=== [5] CAPTURE - resources ==='
docker stats --no-stream

echo '=== [6] Scale to 3 replicas ==='
docker compose --env-file .env.dev up -d --scale app=3 app
docker compose --env-file .env.dev restart proxy
sleep 4
docker compose --env-file .env.dev ps

echo '=== [7] CAPTURE - load balancing ==='
for i in $(seq 1 12); do curl -fsS http://localhost:8080/instance; echo; done
