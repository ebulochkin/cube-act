#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/common.sh
source "$SCRIPT_DIR/common.sh"

require_var DATASET_REPO_ID
require_var DATASET_ROOT
require_var TRAIN_OUTPUT_DIR
require_var TRAIN_STEPS
require_var TRAIN_BATCH_SIZE
require_var TRAIN_NUM_WORKERS
require_var TRAIN_SAVE_FREQ
require_var TRAIN_PREFETCH_FACTOR
require_var TRAIN_POLICY_USE_AMP
require_var TRAIN_DATASET_RETURN_UINT8

export PYTORCH_ALLOC_CONF="${PYTORCH_ALLOC_CONF:-expandable_segments:True}"

lerobot-train \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --dataset.root="$DATASET_ROOT" \
  --dataset.return_uint8="$TRAIN_DATASET_RETURN_UINT8" \
  --policy.type=act \
  --policy.push_to_hub=false \
  --policy.use_amp="$TRAIN_POLICY_USE_AMP" \
  --output_dir="$TRAIN_OUTPUT_DIR" \
  --steps="$TRAIN_STEPS" \
  --batch_size="$TRAIN_BATCH_SIZE" \
  --num_workers="$TRAIN_NUM_WORKERS" \
  --prefetch_factor="$TRAIN_PREFETCH_FACTOR" \
  --save_freq="$TRAIN_SAVE_FREQ" \
  --eval_freq=0
