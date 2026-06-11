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
require_var ROLLOUT_LOOP
require_var ROLLOUT_RETURN_ON_RESET
require_var DISPLAY_DATA
require_var POLICY_TEMPORAL_ENSEMBLE_COEFF
require_var POLICY_N_ACTION_STEPS

cameras="$(robot_cameras_json)"
duration="$ROLLOUT_DURATION_S"

policy_args=(
  --policy.path="$POLICY_PATH"
  --policy.n_action_steps="$POLICY_N_ACTION_STEPS"
)

if [[ "$POLICY_TEMPORAL_ENSEMBLE_COEFF" != "none" ]]; then
  policy_args+=(--policy.temporal_ensemble_coeff="$POLICY_TEMPORAL_ENSEMBLE_COEFF")
fi

run_rollout() {
  if [[ "$ROLLOUT_LOOP" == "true" ]]; then
    export LEROBOT_ROLLOUT_RESET_INTERVAL_S="$ROLLOUT_DURATION_S"
    export LEROBOT_ROLLOUT_RETURN_ON_RESET="$ROLLOUT_RETURN_ON_RESET"
    duration=0
  fi

  lerobot-rollout \
    --strategy.type=base \
    "${policy_args[@]}" \
    --robot.type="$ROBOT_TYPE" \
    --robot.port="$ROBOT_PORT" \
    --robot.id="$ROBOT_ID" \
    --robot.cameras="$cameras" \
    --task="$TASK_DESCRIPTION" \
    --fps="$CONTROL_FPS" \
    --duration="$duration" \
    --display_data="$DISPLAY_DATA"
}

if [[ "$ROLLOUT_LOOP" == "true" ]]; then
  run_rollout
else
  run_rollout
fi
