# cube-act

Imitation learning pipeline for a SO-101 cube-pick setup with three cameras:

- overhead: ZED 2, published through a tiny `pyzed` to LeRobot ZMQ bridge
- side: Intel RealSense D435i, using LeRobot's built-in RealSense camera
- wrist/gripper: Intel RealSense D405, using LeRobot's built-in RealSense camera

The scripts are intentionally thin wrappers around official LeRobot commands. The only custom part is
`scripts/zed2_zmq_publisher.py`, because ZED 2 is not a built-in LeRobot camera.

## Workstation Setup

On the robot workstation:

```bash
git clone https://github.com/huggingface/lerobot.git
cd lerobot
pip install -e ".[core_scripts,training,intelrealsense,pyzmq-dep]"
```

Install camera SDKs:

- Intel RealSense SDK + `pyrealsense2`
- ZED SDK + ZED Python API (`pyzed`)
- `pyzmq` and `opencv-python`, if they are not already present

Then configure this project:

```bash
cp config.env.example config.env
$EDITOR config.env
```

Fill in:

- `ROBOT_PORT` and `TELEOP_PORT`
- `D435I_SERIAL_OR_NAME` and `D405_SERIAL_OR_NAME`
- `HF_USER`, `DATASET_REPO_ID`, and `TASK_DESCRIPTION`

## Pipeline

Find ports and camera IDs:

```bash
./scripts/00_find_hardware.sh
```

Calibrate follower and leader:

```bash
./scripts/01_calibrate.sh
```

Start the ZED 2 overhead stream in its own terminal:

```bash
./scripts/start_zed2_overhead.sh
```

Record demonstrations:

```bash
./scripts/02_record_dataset.sh
```

Train ACT on the recorded dataset:

```bash
./scripts/03_train_act.sh
```

If `TRAIN_OUTPUT_DIR` already exists, LeRobot will stop unless you resume or choose a new output directory.

Run policy inference on the robot:

```bash
./scripts/04_rollout_policy.sh
```

Optionally replay an episode back on the robot:

```bash
./scripts/05_replay_episode.sh 0
```

## Camera Config

The generated LeRobot camera config has this shape:

```json
{
  "overhead": {"type": "zmq", "server_address": "127.0.0.1", "port": 5555, "camera_name": "overhead"},
  "side": {"type": "intelrealsense", "serial_number_or_name": "D435I_SERIAL"},
  "wrist": {"type": "intelrealsense", "serial_number_or_name": "D405_SERIAL"}
}
```

Keep the ZED publisher running while recording or rolling out. If the ZED is on another machine,
set `ZED_SERVER_ADDRESS` in `config.env` to that machine's IP and leave the LeRobot commands unchanged.

References used for the command flow:

- https://huggingface.co/docs/lerobot/en/il_robots
- https://huggingface.co/docs/lerobot/en/so101
- https://github.com/huggingface/lerobot
