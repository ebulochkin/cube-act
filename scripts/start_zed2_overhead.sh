#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_camera_config
require_var ZED_JPEG_QUALITY
require_var ZED_DEBUG_STATS
require_var ZED_WARMUP_FRAMES
require_var ZED_OPEN_RETRIES
require_var ZED_OPEN_RETRY_SLEEP_S
require_var ZED_AUTO_EXPOSURE
require_var ZED_EXPOSURE
require_var ZED_GAIN
require_var ZED_LED

args=(
  --port "$ZED_ZMQ_PORT" \
  --camera-name "$ZED_CAMERA_NAME" \
  --fps "$ZED_FPS" \
  --width "$ZED_WIDTH" \
  --height "$ZED_HEIGHT" \
  --jpeg-quality "$ZED_JPEG_QUALITY" \
  --warmup-frames "$ZED_WARMUP_FRAMES" \
  --open-retries "$ZED_OPEN_RETRIES" \
  --open-retry-sleep-s "$ZED_OPEN_RETRY_SLEEP_S"
)

if [[ "$ZED_DEBUG_STATS" == "true" ]]; then
  args+=(--debug-stats)
fi

if [[ "$ZED_AUTO_EXPOSURE" == "true" ]]; then
  args+=(--auto-exposure)
else
  args+=(--exposure "$ZED_EXPOSURE" --gain "$ZED_GAIN")
fi

if [[ "$ZED_LED" == "true" ]]; then
  args+=(--led)
fi

if [[ -n "${ZED_SAVE_FIRST_FRAME:-}" ]]; then
  args+=(--save-first-frame "$ZED_SAVE_FIRST_FRAME")
fi

python "$SCRIPT_DIR/zed2_zmq_publisher.py" "${args[@]}"
