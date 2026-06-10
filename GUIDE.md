# GUIDE

Это пошаговая инструкция для запуска полного пайплайна: от проверки железа и записи демонстраций до обучения ACT и инференса на SO-101.

ZED 2 больше не используется. Камеры теперь все через встроенную поддержку Intel RealSense в LeRobot:

- `overhead`: Intel RealSense D455
- `side`: Intel RealSense D435i
- `wrist`: Intel RealSense D405

## 1. Что Должно Быть Подключено

Железо:

- SO-101 follower robot
- SO-101 leader для teleoperation
- Intel RealSense D455 overhead camera
- Intel RealSense D435i side camera
- Intel RealSense D405 wrist/gripper camera

Софт на рабочем компьютере:

- Linux/Ubuntu workstation с доступом к USB-устройствам
- Python окружение для LeRobot
- Intel RealSense SDK
- `pyrealsense2`
- аккаунт Hugging Face, если датасет или модель нужно пушить на Hub

## 2. Установка LeRobot

LeRobot лучше держать отдельным репозиторием, а не клонировать внутрь `cube-act`. Например:

```bash
mkdir -p ~/code
git clone https://github.com/huggingface/lerobot.git ~/code/lerobot
cd ~/code/lerobot
pip install -e ".[core_scripts,training,intelrealsense]"
```

`cube-act` при этом остается отдельной папкой, например:

```bash
git clone <your_cube_act_repo_url> ~/code/cube-act
cd ~/code/cube-act
```

Наши скрипты не импортируют LeRobot по относительному пути и не ожидают папку `lerobot` внутри проекта. Они вызывают установленные CLI-команды:

- `lerobot-record`
- `lerobot-train`
- `lerobot-rollout`
- `lerobot-calibrate`
- `lerobot-find-port`
- `lerobot-find-cameras`

Проверка:

```bash
which lerobot-record
lerobot-find-port --help
lerobot-find-cameras realsense
```

## 3. Настройка config.env

В корне `cube-act`:

```bash
cp config.env.example config.env
$EDITOR config.env
```

Основные поля:

```bash
HF_USER=your_hf_username
DATASET_REPO_ID=your_hf_username/so101_cube_pick
TASK_DESCRIPTION="Pick up the cube"
```

Порты робота и leader:

```bash
ROBOT_PORT=/dev/ttyACM0
TELEOP_PORT=/dev/ttyACM1
```

Серийники камер:

```bash
D455_SERIAL_OR_NAME=replace_with_d455_serial
D435I_SERIAL_OR_NAME=replace_with_d435i_serial
D405_SERIAL_OR_NAME=replace_with_d405_serial
```

Параметры записи:

```bash
CONTROL_FPS=30
NUM_EPISODES=50
EPISODE_TIME_S=30
RESET_TIME_S=10
PUSH_TO_HUB=false
```

Стабильный recording preset:

```bash
DISPLAY_DATA=false
DISPLAY_COMPRESSED_IMAGES=true
DATASET_STREAMING_ENCODING=false
DATASET_IMAGE_WRITER_PROCESSES=1
DATASET_IMAGE_WRITER_THREADS_PER_CAMERA=4
DATASET_CAMERA_VCODEC=h264
```

`DATASET_STREAMING_ENCODING=false` означает, что LeRobot пишет изображения асинхронно, а видео кодирует после эпизода. Это обычно стабильнее для control loop, чем live encoding внутри записи.

Параметры обучения:

```bash
TRAIN_OUTPUT_DIR=outputs/train/so101_cube_act
TRAIN_STEPS=100000
TRAIN_BATCH_SIZE=32
TRAIN_NUM_WORKERS=8
```

Для RTX 4090 это нормальный стартовый конфиг. Если память GPU забивается, уменьши `TRAIN_BATCH_SIZE` до `16`. Если память остается свободной, можно попробовать `48` или `64`.

## 4. Поиск Портов И Камер

Запусти:

```bash
./scripts/00_find_hardware.sh
```

Скрипт вызывает:

- `lerobot-find-port`
- `lerobot-find-cameras realsense`
- `lerobot-find-cameras opencv`

Из вывода нужно взять:

- порт follower arm
- порт leader arm
- serial/name D455
- serial/name D435i
- serial/name D405

После этого обнови `config.env`.

## 5. Калибровка SO-101

Запусти:

```bash
./scripts/01_calibrate.sh
```

Скрипт по очереди вызывает:

```bash
lerobot-calibrate --robot.type=so101_follower ...
lerobot-calibrate --teleop.type=so101_leader ...
```

Калибровку нужно пройти перед записью демонстраций. Если менялись моторы, порты, сборка руки или leader, лучше перекалибровать.

## 6. Запись Датасета

Убедись, что:

- follower и leader подключены
- все три RealSense камеры видны через `lerobot-find-cameras realsense`
- `config.env` заполнен
- никакие камеры не открыты в RealSense Viewer

Запуск записи:

```bash
./scripts/02_record_dataset.sh
```

Скрипт вызывает `lerobot-record` с тремя камерами:

- `overhead`: `type=intelrealsense`, D455
- `side`: `type=intelrealsense`, D435i
- `wrist`: `type=intelrealsense`, D405

Сгенерированный camera config имеет такой вид:

```json
{
  "overhead": {
    "type": "intelrealsense",
    "serial_number_or_name": "D455_SERIAL",
    "width": 640,
    "height": 480,
    "fps": 30
  },
  "side": {
    "type": "intelrealsense",
    "serial_number_or_name": "D435I_SERIAL",
    "width": 640,
    "height": 480,
    "fps": 30
  },
  "wrist": {
    "type": "intelrealsense",
    "serial_number_or_name": "D405_SERIAL",
    "width": 640,
    "height": 480,
    "fps": 30
  }
}
```

Для отладки лучше начинать так:

```bash
NUM_EPISODES=2
PUSH_TO_HUB=false
DISPLAY_DATA=false
DATASET_STREAMING_ENCODING=false
```

Когда локальная запись стабильно держит FPS, можно вернуть:

```bash
NUM_EPISODES=50
PUSH_TO_HUB=true
```

Если запись прервалась и нужно продолжить тот же датасет:

```bash
RESUME_RECORDING=true
```

## 7. Проверка Или Replay Эпизода

После записи можно проиграть действия из эпизода обратно на роботе:

```bash
./scripts/05_replay_episode.sh 0
```

Для другого эпизода:

```bash
./scripts/05_replay_episode.sh 3
```

## 8. Обучение ACT

Запуск:

```bash
./scripts/03_train_act.sh
```

Скрипт вызывает:

```bash
lerobot-train \
  --dataset.repo_id="$DATASET_REPO_ID" \
  --policy.type=act \
  --output_dir="$TRAIN_OUTPUT_DIR"
```

Важно: если `TRAIN_OUTPUT_DIR` уже существует, LeRobot остановится, чтобы не перезаписать прошлый запуск. В таком случае выбери новый путь или вручную настрой resume.

После обучения ожидаемый путь к модели:

```bash
outputs/train/so101_cube_act/checkpoints/last/pretrained_model
```

Этот путь должен совпадать с `POLICY_PATH` в `config.env`.

Для ACT лучше держать одинаковое разрешение всех image inputs:

```bash
OVERHEAD_REALSENSE_WIDTH=640
OVERHEAD_REALSENSE_HEIGHT=480
OVERHEAD_REALSENSE_WARMUP_S=15
SIDE_REALSENSE_WIDTH=640
SIDE_REALSENSE_HEIGHT=480
SIDE_REALSENSE_WARMUP_S=15
WRIST_REALSENSE_WIDTH=640
WRIST_REALSENSE_HEIGHT=480
WRIST_REALSENSE_WARMUP_S=15
```

## 9. Инференс На Роботе

Запуск:

```bash
./scripts/04_rollout_policy.sh
```

Скрипт вызывает `lerobot-rollout`:

```bash
lerobot-rollout \
  --strategy.type=base \
  --policy.path="$POLICY_PATH" \
  --robot.type=so101_follower \
  --robot.cameras="..."
```

Длительность rollout задается:

```bash
ROLLOUT_DURATION_S=60
```

Это один непрерывный live rollout на 60 секунд, не N отдельных эпизодов.

## 10. Частые Проблемы

`Missing config.env`:

```bash
cp config.env.example config.env
```

RealSense камера не находится:

- проверь USB-порт и питание
- запусти `./scripts/00_find_hardware.sh`
- обнови `D455_SERIAL_OR_NAME`, `D435I_SERIAL_OR_NAME`, `D405_SERIAL_OR_NAME`
- убедись, что установлен `pyrealsense2`
- закрой RealSense Viewer, если он открыт
- если раньше ставился локальный ZED plugin, удали его из окружения: `pip uninstall -y lerobot_camera_zed`

Одна из камер не отдает кадры:

- увеличь warmup проблемной камеры, например `OVERHEAD_REALSENSE_WARMUP_S=30`
- попробуй снизить FPS на проблемной камере до `15`
- проверь USB3 порт и кабель
- не подключай все камеры через слабый USB-хаб

Record loop падает до 10-15 FPS:

- поставь `DISPLAY_DATA=false`
- поставь `DATASET_STREAMING_ENCODING=false`
- оставь `DATASET_IMAGE_WRITER_PROCESSES=1`
- временно поставь `CONTROL_FPS=15` для проверки

Encoder thread падает с `expected str, got int`:

- не используй `DATASET_CAMERA_VCODEC=auto`
- поставь `DATASET_CAMERA_VCODEC=h264`

Обучение падает из-за существующего `TRAIN_OUTPUT_DIR`:

- поменяй `TRAIN_OUTPUT_DIR`
- или настрой resume вручную, если хочешь продолжить старый запуск

## 11. Файлы

- `config.env.example`: шаблон локального конфига
- `scripts/common.sh`: общие функции и генерация camera JSON
- `scripts/00_find_hardware.sh`: поиск портов и камер
- `scripts/01_calibrate.sh`: калибровка follower и leader
- `scripts/02_record_dataset.sh`: запись демонстраций
- `scripts/03_train_act.sh`: обучение ACT
- `scripts/04_rollout_policy.sh`: rollout обученной политики
- `scripts/05_replay_episode.sh`: replay эпизода

## 12. Официальные Референсы

- https://huggingface.co/docs/lerobot/en/il_robots
- https://huggingface.co/docs/lerobot/en/so101
- https://github.com/huggingface/lerobot
