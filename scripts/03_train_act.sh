#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_var DATASET_REPO_ID
require_var TRAIN_OUTPUT_DIR
require_var TRAIN_STEPS
require_var TRAIN_BATCH_SIZE
require_var TRAIN_NUM_WORKERS

lerobot-train \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --policy.type=act \
  --output_dir="$TRAIN_OUTPUT_DIR" \
  --steps="$TRAIN_STEPS" \
  --batch_size="$TRAIN_BATCH_SIZE" \
  --num_workers="$TRAIN_NUM_WORKERS" \
  --save_freq=20000 \
  --eval_freq=0
