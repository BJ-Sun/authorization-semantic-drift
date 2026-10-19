#!/bin/sh
set -eu

LAB_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEFAULT_RUNTIME_DIR="$LAB_DIR/../attack-generation/openclaw-runtime"
OPENCLAW_RUNTIME_DIR=${OPENCLAW_RUNTIME_DIR:-$DEFAULT_RUNTIME_DIR}
RUNTIME_DIR=$(CDPATH= cd -- "$OPENCLAW_RUNTIME_DIR" && pwd)
ASD_DOCKER_BIN=${ASD_DOCKER_BIN:-docker}

if [ "$(git -C "$RUNTIME_DIR" rev-parse HEAD)" != "ea21d360924a53b8ec941c84c29423739d31725f" ]; then
  echo "warning: the artifact was validated against OpenClaw commit ea21d360924a53b8ec941c84c29423739d31725f" >&2
fi

"$ASD_DOCKER_BIN" build \
  --build-arg OPENCLAW_EXTENSIONS=deepseek \
  -t asd-openclaw:2026.9.2 \
  "$RUNTIME_DIR"
"$ASD_DOCKER_BIN" build -t asd-lab:pilot -f "$LAB_DIR/Dockerfile.lab" "$LAB_DIR"

