#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_camera_config
require_var ZED_JPEG_QUALITY

python "$SCRIPT_DIR/zed2_zmq_publisher.py" \
  --port "$ZED_ZMQ_PORT" \
  --camera-name "$ZED_CAMERA_NAME" \
  --fps "$ZED_FPS" \
  --width "$ZED_WIDTH" \
  --height "$ZED_HEIGHT" \
  --jpeg-quality "$ZED_JPEG_QUALITY"
