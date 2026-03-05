#!/usr/bin/env bash
set -e

if command -v nvidia-smi &>/dev/null && nvidia-smi &>/dev/null 2>&1; then
  echo "[rss-reader] NVIDIA GPU detected — starting with GPU support"
  docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d "$@"
else
  echo "[rss-reader] No GPU detected — starting with CPU"
  docker compose up -d "$@"
fi
