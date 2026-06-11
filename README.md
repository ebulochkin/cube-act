# cube-act

Пайплайн imitation learning для задачи поднятия кубика роботом SO-101 через LeRobot.

Конфигурация сенсоров теперь полностью на Intel RealSense:

- `overhead`: Intel RealSense D455 сверху
- `side`: Intel RealSense D435i сбоку
- `wrist`: Intel RealSense D405 на гриппере

Скрипты в этом репозитории являются тонкими обертками над официальными CLI-командами LeRobot:

- `lerobot-find-port`
- `lerobot-find-cameras`
- `lerobot-calibrate`
- `lerobot-record`
- `lerobot-train`
- `lerobot-rollout`
- `lerobot-replay`

ZED 2 больше не используется. Отдельный camera publisher, ZMQ-мост и локальный ZED plugin не нужны.

## Быстрый Старт

LeRobot не нужно клонировать внутрь этого репозитория. Держи его отдельно, например:

```bash
mkdir -p ~/code
git clone https://github.com/huggingface/lerobot.git ~/code/lerobot
cd ~/code/lerobot
pip install -e ".[core_scripts,training,intelrealsense]"
```

После этого команды `lerobot-record`, `lerobot-train`, `lerobot-rollout` должны быть доступны в текущем Python окружении.

В `cube-act`:

```bash
cp config.env.example config.env
$EDITOR config.env
```

После заполнения портов, серийников камер и Hugging Face repo id:

```bash
./scripts/00_find_hardware.sh
./scripts/01_calibrate.sh
```

Затем записать датасет, обучить ACT и запустить политику:

```bash
./scripts/02_record_dataset.sh
./scripts/03_train_act.sh
./scripts/04_rollout_policy.sh
```

По умолчанию запись сохраняется локально в `cache/datasets/so101_cube_pick`, поэтому replay можно запускать без выгрузки на Hugging Face Hub.

Для запуска конкретного checkpoint укажи папку `pretrained_model`:

```bash
POLICY_PATH=remote_checkpoints/so101_cube_act_009250/pretrained_model
./scripts/04_rollout_policy.sh
```

Параметры rollout, temporal ensembling и loop-режима описаны в [GUIDE.md](GUIDE.md).

Полная инструкция по установке, настройке и запуску находится в [GUIDE.md](GUIDE.md).

Для обучения на Vast после clone репозитория можно сразу создать локальное training-окружение:

```bash
./scripts/setup_vast_venv.sh
source .venv/bin/activate
```

Подробный Vast workflow описан в [VAST_TRAINING_MANUAL.md](VAST_TRAINING_MANUAL.md).

## Ссылки

- https://huggingface.co/docs/lerobot/en/il_robots
- https://huggingface.co/docs/lerobot/en/so101
- https://github.com/huggingface/lerobot
