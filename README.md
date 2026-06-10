# cube-act

Пайплайн imitation learning для задачи поднятия кубика роботом SO-101 через LeRobot.

Конфигурация сенсоров:

- `overhead`: ZED 2 сверху, подключается через небольшой мост `pyzed -> ZMQCamera`
- `side`: Intel RealSense D435i сбоку, через встроенную камеру LeRobot
- `wrist`: Intel RealSense D405 на гриппере, через встроенную камеру LeRobot

Скрипты в этом репозитории являются тонкими обертками над официальными CLI-командами LeRobot:

- `lerobot-find-port`
- `lerobot-find-cameras`
- `lerobot-calibrate`
- `lerobot-record`
- `lerobot-train`
- `lerobot-rollout`
- `lerobot-replay`

Единственная кастомная часть: [scripts/zed2_zmq_publisher.py](scripts/zed2_zmq_publisher.py). Она нужна потому, что ZED 2 не поддерживается LeRobot как встроенный тип камеры. Скрипт читает RGB-кадр через `pyzed`, кодирует JPEG и публикует его в формате, который ожидает стандартная LeRobot `ZMQCamera`.

## Быстрый Старт

LeRobot не нужно клонировать внутрь этого репозитория. Держи его отдельно, например:

```bash
mkdir -p ~/code
git clone https://github.com/huggingface/lerobot.git ~/code/lerobot
cd ~/code/lerobot
pip install -e ".[core_scripts,training,intelrealsense,pyzmq-dep]"
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

В отдельном терминале запустить ZED 2:

```bash
./scripts/start_zed2_overhead.sh
```

Затем записать датасет, обучить ACT и запустить политику:

```bash
./scripts/02_record_dataset.sh
./scripts/03_train_act.sh
./scripts/04_rollout_policy.sh
```

Полная инструкция по установке, настройке и запуску находится в [GUIDE.md](GUIDE.md).

## Ссылки

- https://huggingface.co/docs/lerobot/en/il_robots
- https://huggingface.co/docs/lerobot/en/so101
- https://github.com/huggingface/lerobot
