#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

echo "Ports:"
lerobot-find-port || true

echo
echo "RealSense cameras:"
lerobot-find-cameras realsense || true

echo
echo "OpenCV cameras, useful for quick sanity checks:"
lerobot-find-cameras opencv || true
