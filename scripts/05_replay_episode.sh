#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_robot_config
require_var DATASET_REPO_ID
require_var CONTROL_FPS

EPISODE="${1:-0}"

lerobot-replay \
  --robot.type="$ROBOT_TYPE" \
  --robot.port="$ROBOT_PORT" \
  --robot.id="$ROBOT_ID" \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --dataset.episode="$EPISODE" \
  --dataset.fps="$CONTROL_FPS"
