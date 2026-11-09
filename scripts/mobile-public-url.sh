#!/usr/bin/env bash
# Expose local SPA (port 5173) via Cloudflare quick tunnel for mobile testing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon is not running. Start Docker Desktop, then run this script again."
  exit 1
fi

if ! curl -sf http://127.0.0.1:5173/health >/dev/null 2>&1; then
  echo "Starting docker compose (db, api, web)..."
  docker compose up -d --build
  echo "Waiting for web on :5173..."
  for _ in $(seq 1 60); do
    if curl -sf http://127.0.0.1:5173/ >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "Installing cloudflared (Homebrew)..."
  brew install cloudflared
fi

echo ""
echo "Starting public tunnel → http://127.0.0.1:5173"
echo "Open the https://*.trycloudflare.com URL on your phone (same Wi‑Fi not required)."
echo ""
echo "Optional: set PUBLIC_APP_URL to that URL and restart api for password-reset links in logs:"
echo "  PUBLIC_APP_URL=https://YOUR-TUNNEL.trycloudflare.com docker compose up -d api"
echo ""

exec cloudflared tunnel --url http://127.0.0.1:5173
