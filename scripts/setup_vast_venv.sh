#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

VENV_DIR="${VENV_DIR:-$REPO_ROOT/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LEROBOT_DIR="${LEROBOT_DIR:-$HOME/code/lerobot}"
LEROBOT_REF="${LEROBOT_REF:-main}"

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return
  fi

  echo "uv is not installed; installing it with pip..."
  "$PYTHON_BIN" -m pip install --user --upgrade uv
  export PATH="$HOME/.local/bin:$PATH"

  if ! command -v uv >/dev/null 2>&1; then
    echo "uv was installed but is not on PATH. Try: export PATH=\"\$HOME/.local/bin:\$PATH\"" >&2
    exit 1
  fi
}

clone_or_update_lerobot() {
  mkdir -p "$(dirname "$LEROBOT_DIR")"

  if [[ -d "$LEROBOT_DIR/.git" ]]; then
    echo "Using existing LeRobot checkout: $LEROBOT_DIR"
    git -C "$LEROBOT_DIR" fetch --tags origin
  else
    echo "Cloning LeRobot into: $LEROBOT_DIR"
    git clone https://github.com/huggingface/lerobot.git "$LEROBOT_DIR"
  fi

  git -C "$LEROBOT_DIR" checkout "$LEROBOT_REF"
}

main() {
  cd "$REPO_ROOT"

  ensure_uv

  echo "Creating virtual environment: $VENV_DIR"
  uv venv "$VENV_DIR" --python "$PYTHON_BIN"

  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"

  clone_or_update_lerobot

  echo "Installing training dependencies..."
  uv pip install --upgrade pip wheel setuptools
  uv pip install -e "${LEROBOT_DIR}[core_scripts,training]"
  uv pip install huggingface_hub hf_transfer

  echo
  echo "Vast training environment is ready."
  echo "Activate it with:"
  echo "  cd $REPO_ROOT"
  echo "  source .venv/bin/activate"
  echo
  echo "Quick CUDA check:"
  python - <<'PY'
import torch
print(f"torch={torch.__version__}")
print(f"cuda_available={torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"cuda_device={torch.cuda.get_device_name(0)}")
PY
}

main "$@"
