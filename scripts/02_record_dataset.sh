#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_robot_config
require_teleop_config
require_var DATASET_REPO_ID
require_var TASK_DESCRIPTION
require_var CONTROL_FPS
require_var NUM_EPISODES
require_var EPISODE_TIME_S
require_var RESET_TIME_S
require_var PUSH_TO_HUB
require_var RESUME_RECORDING
require_var DISPLAY_DATA

lerobot-record \
  --robot.type="$ROBOT_TYPE" \
  --robot.port="$ROBOT_PORT" \
  --robot.id="$ROBOT_ID" \
  --robot.cameras="$(robot_cameras_json)" \
  --teleop.type="$TELEOP_TYPE" \
  --teleop.port="$TELEOP_PORT" \
  --teleop.id="$TELEOP_ID" \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --dataset.fps="$CONTROL_FPS" \
  --dataset.num_episodes="$NUM_EPISODES" \
  --dataset.single_task="$TASK_DESCRIPTION" \
  --dataset.episode_time_s="$EPISODE_TIME_S" \
  --dataset.reset_time_s="$RESET_TIME_S" \
  --dataset.streaming_encoding=true \
  --dataset.encoder_threads=2 \
  --dataset.push_to_hub="$PUSH_TO_HUB" \
  --resume="$RESUME_RECORDING" \
  --display_data="$DISPLAY_DATA"
