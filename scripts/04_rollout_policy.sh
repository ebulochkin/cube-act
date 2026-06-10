#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_robot_config
require_var POLICY_PATH
require_var TASK_DESCRIPTION
require_var CONTROL_FPS
require_var ROLLOUT_DURATION_S
require_var DISPLAY_DATA

lerobot-rollout \
  --strategy.type=base \
  --policy.path="$POLICY_PATH" \
  --robot.type="$ROBOT_TYPE" \
  --robot.port="$ROBOT_PORT" \
  --robot.id="$ROBOT_ID" \
  --robot.cameras="$(robot_cameras_json)" \
  --task="$TASK_DESCRIPTION" \
  --fps="$CONTROL_FPS" \
  --duration="$ROLLOUT_DURATION_S" \
  --display_data="$DISPLAY_DATA"
