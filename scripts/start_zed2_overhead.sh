#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_camera_config
require_var ZED_JPEG_QUALITY
require_var ZED_DEBUG_STATS

args=(
  --port "$ZED_ZMQ_PORT" \
  --camera-name "$ZED_CAMERA_NAME" \
  --fps "$ZED_FPS" \
  --width "$ZED_WIDTH" \
  --height "$ZED_HEIGHT" \
  --jpeg-quality "$ZED_JPEG_QUALITY"
)

if [[ "$ZED_DEBUG_STATS" == "true" ]]; then
  args+=(--debug-stats)
fi

if [[ -n "${ZED_SAVE_FIRST_FRAME:-}" ]]; then
  args+=(--save-first-frame "$ZED_SAVE_FIRST_FRAME")
fi

python "$SCRIPT_DIR/zed2_zmq_publisher.py" "${args[@]}"
