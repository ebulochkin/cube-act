#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_FILE="${CONFIG_FILE:-$ROOT_DIR/config.env}"

if [[ -f "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
else
  echo "Missing $CONFIG_FILE. Copy config.env.example to config.env and edit it." >&2
  exit 1
fi

require_var() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Required config variable is empty: $name" >&2
    exit 1
  fi
}

require_robot_config() {
  require_var ROBOT_TYPE
  require_var ROBOT_PORT
  require_var ROBOT_ID
}

require_teleop_config() {
  require_var TELEOP_TYPE
  require_var TELEOP_PORT
  require_var TELEOP_ID
}

require_camera_config() {
  require_var ZED_SERVER_ADDRESS
  require_var ZED_ZMQ_PORT
  require_var ZED_CAMERA_NAME
  require_var ZED_WIDTH
  require_var ZED_HEIGHT
  require_var ZED_FPS
  require_var D435I_SERIAL_OR_NAME
  require_var D405_SERIAL_OR_NAME
  require_var REALSENSE_WIDTH
  require_var REALSENSE_HEIGHT
  require_var REALSENSE_FPS
}

robot_cameras_json() {
  require_camera_config

  printf '{"overhead":{"type":"zmq","server_address":"%s","port":%s,"camera_name":"%s","width":%s,"height":%s,"fps":%s},"side":{"type":"intelrealsense","serial_number_or_name":"%s","width":%s,"height":%s,"fps":%s},"wrist":{"type":"intelrealsense","serial_number_or_name":"%s","width":%s,"height":%s,"fps":%s}}' \
    "$ZED_SERVER_ADDRESS" "$ZED_ZMQ_PORT" "$ZED_CAMERA_NAME" "$ZED_WIDTH" "$ZED_HEIGHT" "$ZED_FPS" \
    "$D435I_SERIAL_OR_NAME" "$REALSENSE_WIDTH" "$REALSENSE_HEIGHT" "$REALSENSE_FPS" \
    "$D405_SERIAL_OR_NAME" "$REALSENSE_WIDTH" "$REALSENSE_HEIGHT" "$REALSENSE_FPS"
}
