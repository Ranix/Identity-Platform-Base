#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Safe with a single replica (Wave 1). With multiple replicas (Wave 3+), concurrent
# `alembic upgrade head` calls race — move this to a pre-deploy step before scaling out.
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
