#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_robot_config
require_teleop_config
require_var DATASET_REPO_ID
require_var DATASET_ROOT
require_var TASK_DESCRIPTION
require_var CONTROL_FPS
require_var NUM_EPISODES
require_var EPISODE_TIME_S
require_var RESET_TIME_S
require_var PUSH_TO_HUB
require_var RESUME_RECORDING
require_var DISPLAY_DATA
require_var DISPLAY_COMPRESSED_IMAGES
require_var DATASET_STREAMING_ENCODING
require_var DATASET_ENCODER_QUEUE_MAXSIZE
require_var DATASET_ENCODER_THREADS
require_var DATASET_CAMERA_VCODEC
require_var DATASET_CAMERA_CRF
require_var DATASET_IMAGE_WRITER_PROCESSES
require_var DATASET_IMAGE_WRITER_THREADS_PER_CAMERA

cameras="$(robot_cameras_json)"

lerobot-record \
  --robot.type="$ROBOT_TYPE" \
  --robot.port="$ROBOT_PORT" \
  --robot.id="$ROBOT_ID" \
  --robot.cameras="$cameras" \
  --teleop.type="$TELEOP_TYPE" \
  --teleop.port="$TELEOP_PORT" \
  --teleop.id="$TELEOP_ID" \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --dataset.root="$DATASET_ROOT" \
  --dataset.fps="$CONTROL_FPS" \
  --dataset.num_episodes="$NUM_EPISODES" \
  --dataset.single_task="$TASK_DESCRIPTION" \
  --dataset.episode_time_s="$EPISODE_TIME_S" \
  --dataset.reset_time_s="$RESET_TIME_S" \
  --dataset.streaming_encoding="$DATASET_STREAMING_ENCODING" \
  --dataset.encoder_queue_maxsize="$DATASET_ENCODER_QUEUE_MAXSIZE" \
  --dataset.encoder_threads="$DATASET_ENCODER_THREADS" \
  --dataset.camera_encoder.vcodec="$DATASET_CAMERA_VCODEC" \
  --dataset.camera_encoder.crf="$DATASET_CAMERA_CRF" \
  --dataset.num_image_writer_processes="$DATASET_IMAGE_WRITER_PROCESSES" \
  --dataset.num_image_writer_threads_per_camera="$DATASET_IMAGE_WRITER_THREADS_PER_CAMERA" \
  --dataset.push_to_hub="$PUSH_TO_HUB" \
  --resume="$RESUME_RECORDING" \
  --display_data="$DISPLAY_DATA" \
  --display_compressed_images="$DISPLAY_COMPRESSED_IMAGES"
