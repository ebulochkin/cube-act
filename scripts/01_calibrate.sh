#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_robot_config
require_teleop_config

lerobot-calibrate \
  --robot.type="$ROBOT_TYPE" \
  --robot.port="$ROBOT_PORT" \
  --robot.id="$ROBOT_ID"

lerobot-calibrate \
  --teleop.type="$TELEOP_TYPE" \
  --teleop.port="$TELEOP_PORT" \
  --teleop.id="$TELEOP_ID"
