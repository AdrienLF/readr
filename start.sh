#!/usr/bin/env bash
set -e

# ── NVIDIA GPU ─────────────────────────────────────────────────────────────────
if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null 2>&1; then
  echo "[readr] NVIDIA GPU detected — starting with GPU support"
  docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d "$@"

# ── CPU (macOS, no-GPU Linux) ──────────────────────────────────────────────────
else
  echo "[readr] Starting (CPU inference)"
  docker compose up -d "$@"
fi
