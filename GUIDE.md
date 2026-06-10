# GUIDE

Это пошаговая инструкция для запуска полного пайплайна: от проверки железа и записи демонстраций до обучения ACT и инференса на SO-101.

## 1. Что Должно Быть Подключено

Железо:

- SO-101 follower robot
- SO-101 leader для teleoperation
- ZED 2 overhead camera
- Intel RealSense D435i side camera
- Intel RealSense D405 wrist/gripper camera

Софт на рабочем компьютере:

- Linux/Ubuntu workstation с доступом к USB-устройствам
- Python окружение для LeRobot
- Intel RealSense SDK
- ZED SDK и Python API `pyzed`
- аккаунт Hugging Face, если датасет или модель нужно пушить на Hub

## 2. Установка LeRobot

LeRobot лучше держать отдельным репозиторием, а не клонировать внутрь `cube-act`. Например:

```bash
mkdir -p ~/code
git clone https://github.com/huggingface/lerobot.git ~/code/lerobot
cd ~/code/lerobot
pip install -e ".[core_scripts,training,intelrealsense,pyzmq-dep]"
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

Поэтому важно только одно: перед запуском скриптов должно быть активировано то Python окружение, где установлен LeRobot.

В `cube-act` также нужно установить локальный camera plugin для ZED:

```bash
cd ~/code/cube-act
pip install -e .
```

После этого LeRobot будет автоматически импортировать пакет `lerobot_camera_zed` и понимать camera config `type=zed`.

Дополнительно установи SDK камер:

- Intel RealSense SDK и `pyrealsense2`
- ZED SDK и Python API `pyzed`
- `opencv-python`, если его нет в окружении

Для ZED SDK важно: Python API нужно поставить именно в активное окружение LeRobot. Если окружение называется `lerobot_pure`, сначала активируй его, потом установи `pyzed`:

```bash
conda activate lerobot_pure
pip uninstall -y pyzed
cd /usr/local/zed
python get_python_api.py
```

Проверка:

```bash
python -c "import pyzed.sl as sl; print('pyzed.sl ok')"
```

Не ставь ZED Python API командой `pip install pyzed`: это другой PyPI-пакет. Если `python -c "import pyzed; print(pyzed.__file__)"` показывает файл вроде `site-packages/pyzed.py`, значит установлен неправильный пакет, его нужно удалить через `pip uninstall -y pyzed`.

Если `/usr/local/zed/get_python_api.py` отсутствует, значит ZED SDK не установлен или установлен в другое место. Сначала поставь ZED SDK с сайта Stereolabs, затем повтори команды выше.

Если `python get_python_api.py` долго висит на проверке URL или скачивании, можно поставить wheel вручную. Для ZED SDK 5.3 и Python 3.12:

```bash
conda activate lerobot_pure
pip uninstall -y pyzed

cd /tmp
wget --show-progress --timeout=30 --tries=3 \
  https://download.stereolabs.com/zedsdk/5.3/whl/linux_x86_64/pyzed-5.3-cp312-cp312-linux_x86_64.whl

pip install /tmp/pyzed-5.3-cp312-cp312-linux_x86_64.whl
python -c "import pyzed.sl as sl; print('pyzed.sl ok')"
```

Если `wget` тоже не скачивает, скачай этот `.whl` на другой машине и перенеси на workstation через `scp`, затем выполни `pip install /path/to/pyzed-5.3-cp312-cp312-linux_x86_64.whl`.

Проверка, что CLI LeRobot доступны:

```bash
which lerobot-record
lerobot-find-port --help
lerobot-record --help
lerobot-train --help
lerobot-rollout --help
```

## 3. Настройка Этого Репозитория

В корне `cube-act`:

```bash
cp config.env.example config.env
$EDITOR config.env
```

Заполни основные поля:

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
DATASET_STREAMING_ENCODING=false
DATASET_ENCODER_QUEUE_MAXSIZE=120
DATASET_ENCODER_THREADS=1
DATASET_CAMERA_VCODEC=h264
DATASET_CAMERA_CRF=30
DATASET_IMAGE_WRITER_PROCESSES=1
DATASET_IMAGE_WRITER_THREADS_PER_CAMERA=4
```

Для стабильной записи с тремя камерами лучше начинать с `DATASET_STREAMING_ENCODING=false`. Тогда LeRobot пишет изображения асинхронно, а видео кодирует после эпизода, не в live control loop. Если включать live encoding, начинай с `DATASET_CAMERA_VCODEC=h264`: дефолтный `libsvtav1` сильно грузит CPU, а `auto` может выбрать `h264_nvenc`; в некоторых версиях LeRobot/PyAV NVENC падает в encoder thread с ошибкой типа `expected str, got int`.

Параметры обучения:

```bash
TRAIN_OUTPUT_DIR=outputs/train/so101_cube_act
TRAIN_STEPS=100000
TRAIN_BATCH_SIZE=32
TRAIN_NUM_WORKERS=8
```

Для RTX 4090 это нормальный стартовый конфиг. Если память GPU забивается, уменьши `TRAIN_BATCH_SIZE` до `16`. Если память остается свободной и dataloader успевает, можно попробовать `48` или `64`.

Путь к политике для инференса:

```bash
POLICY_PATH=outputs/train/so101_cube_act/checkpoints/last/pretrained_model
```

`config.env` не коммитится в git, потому что там локальные порты, серийники и потенциально приватные настройки.

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

Калибровку нужно пройти перед записью демонстраций. Если менялись моторы, порты, сборка руки или лидер, лучше перекалибровать.

## 6. Запуск ZED 2 Overhead Камеры

ZED 2 работает отдельным процессом. Открой отдельный терминал в `cube-act` и запусти:

```bash
./scripts/start_zed2_overhead.sh
```

Этот скрипт запускает:

```bash
python scripts/zed2_zmq_publisher.py
```

Паблишер отдает кадры по ZMQ. LeRobot видит эту камеру как:

```json
{
  "type": "zmq",
  "server_address": "127.0.0.1",
  "port": 5555,
  "camera_name": "overhead"
}
```

Оставь этот терминал открытым во время записи датасета и во время rollout.

Если ZED 2 подключена к другой машине, поставь в `config.env` IP той машины:

```bash
ZED_CAMERA_BACKEND=zmq
ZED_SERVER_ADDRESS=192.168.x.x
```

Обычный рекомендуемый режим для записи на этой машине:

```bash
ZED_CAMERA_BACKEND=native
```

В этом режиме отдельный `start_zed2_overhead.sh` не нужен: LeRobot сам откроет ZED как camera plugin.

## 7. Запись Датасета

Убедись, что:

- follower и leader подключены
- RealSense камеры видны
- ZED publisher запущен в отдельном терминале
- `config.env` заполнен

Запуск записи:

```bash
./scripts/02_record_dataset.sh
```

Скрипт вызывает `lerobot-record` с тремя камерами:

- `overhead`: `type=zed`
- `side`: `type=intelrealsense`
- `wrist`: `type=intelrealsense`

Сгенерированный camera config имеет такой вид:

```json
{
  "overhead": {
    "type": "zed",
    "camera_name": "overhead",
    "zed_resolution": "HD720",
    "camera_name": "overhead",
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

Если запись прервалась и нужно продолжить тот же датасет, поставь:

```bash
RESUME_RECORDING=true
```

Если нужно загрузить датасет на Hugging Face Hub:

```bash
PUSH_TO_HUB=true
```

## 8. Проверка Или Replay Эпизода

После записи можно проиграть действия из эпизода обратно на роботе:

```bash
./scripts/05_replay_episode.sh 0
```

Число `0` означает episode index. Для другого эпизода:

```bash
./scripts/05_replay_episode.sh 3
```

## 9. Обучение ACT

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

Для ACT лучше держать одинаковое разрешение всех image inputs. Поэтому в `config.env.example` стоит:

```bash
ZED_WIDTH=640
ZED_HEIGHT=480
SIDE_REALSENSE_WIDTH=640
SIDE_REALSENSE_HEIGHT=480
WRIST_REALSENSE_WIDTH=640
WRIST_REALSENSE_HEIGHT=480
```

Это особенно важно для трех камер: overhead, side и wrist.

После обучения ожидаемый путь к модели:

```bash
outputs/train/so101_cube_act/checkpoints/last/pretrained_model
```

Этот путь должен совпадать с `POLICY_PATH` в `config.env`.

## 10. Инференс На Роботе

Перед rollout снова запусти ZED publisher в отдельном терминале:

```bash
./scripts/start_zed2_overhead.sh
```

В другом терминале:

```bash
./scripts/04_rollout_policy.sh
```

Скрипт вызывает `lerobot-rollout` в `base` strategy:

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

## 11. Типичный Порядок Терминалов

Терминал 1, ZED 2:

```bash
./scripts/start_zed2_overhead.sh
```

Терминал 2, запись:

```bash
./scripts/02_record_dataset.sh
```

После записи, терминал 2, обучение:

```bash
./scripts/03_train_act.sh
```

После обучения, терминал 1 снова должен держать ZED publisher, терминал 2:

```bash
./scripts/04_rollout_policy.sh
```

## 12. Частые Проблемы

`Missing config.env`:

```bash
cp config.env.example config.env
```

RealSense камера не находится:

- проверь USB-порт и питание
- запусти `./scripts/00_find_hardware.sh`
- обнови `D435I_SERIAL_OR_NAME` и `D405_SERIAL_OR_NAME`
- убедись, что установлен `pyrealsense2`

ZED publisher не стартует:

- проверь, что установлен ZED SDK
- проверь, что Python видит `pyzed`
- проверь, что ZED 2 доступна не из другого процесса

Проверка `pyzed`:

```bash
python -c "import pyzed.sl as sl; print('pyzed.sl ok')"
```

Если видишь ошибку `pyzed is not installed`, установи Python API ZED SDK в активное окружение:

```bash
conda activate lerobot_pure
pip uninstall -y pyzed
cd /usr/local/zed
python get_python_api.py
```

Если ошибка выглядит так: `'pyzed' is not a package`, проверь путь:

```bash
python -c "import pyzed; print(pyzed.__file__)"
```

Если вывод похож на `.../site-packages/pyzed.py`, это неправильный PyPI-пакет. Удали его:

```bash
pip uninstall -y pyzed
```

Потом снова поставь API из ZED SDK:

```bash
cd /usr/local/zed
python get_python_api.py
```

Если `get_python_api.py` зависает на скачивании, ставь wheel напрямую:

```bash
cd /tmp
wget --show-progress --timeout=30 --tries=3 \
  https://download.stereolabs.com/zedsdk/5.3/whl/linux_x86_64/pyzed-5.3-cp312-cp312-linux_x86_64.whl
pip install /tmp/pyzed-5.3-cp312-cp312-linux_x86_64.whl
```

`ZMQCamera timeout` во время записи или rollout:

- проверь, что `./scripts/start_zed2_overhead.sh` запущен
- проверь `ZED_SERVER_ADDRESS`
- проверь, что порт `ZED_ZMQ_PORT` совпадает в publisher и LeRobot config
- если ошибка выглядит как `latest frame is too old`, снизь нагрузку: `DATASET_STREAMING_ENCODING=false`, `DISPLAY_COMPRESSED_IMAGES=true`, `DATASET_IMAGE_WRITER_PROCESSES=1`, `DATASET_IMAGE_WRITER_THREADS_PER_CAMERA=4`, `ZED_JPEG_QUALITY=70`, при необходимости `CONTROL_FPS=15`
- если encoder thread падает с `expected str, got int` после `DATASET_CAMERA_VCODEC=auto`, поставь `DATASET_CAMERA_VCODEC=h264`; это обход проблемы с `h264_nvenc`

LeRobot не понимает RealSense camera type:

- в этом пайплайне используется `type=intelrealsense`
- установи LeRobot с extra `intelrealsense`

Обучение падает из-за существующего `TRAIN_OUTPUT_DIR`:

- поменяй `TRAIN_OUTPUT_DIR`
- или настрой resume вручную, если хочешь продолжить старый запуск

## 13. Файлы

- `config.env.example`: шаблон локального конфига
- `scripts/common.sh`: общие функции и генерация camera JSON
- `scripts/00_find_hardware.sh`: поиск портов и камер
- `scripts/01_calibrate.sh`: калибровка follower и leader
- `scripts/start_zed2_overhead.sh`: запуск ZED publisher
- `scripts/zed2_zmq_publisher.py`: мост ZED 2 в LeRobot ZMQCamera
- `scripts/02_record_dataset.sh`: запись демонстраций
- `scripts/03_train_act.sh`: обучение ACT
- `scripts/04_rollout_policy.sh`: rollout обученной политики
- `scripts/05_replay_episode.sh`: replay эпизода

## 14. Официальные Референсы

- https://huggingface.co/docs/lerobot/en/il_robots
- https://huggingface.co/docs/lerobot/en/so101
- https://github.com/huggingface/lerobot
