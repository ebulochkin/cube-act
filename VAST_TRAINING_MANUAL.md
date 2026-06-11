# Vast training manual

Этот документ описывает полный процесс обучения ACT на Vast: подключение, установка окружения, загрузка датасета, запуск training в `tmux`, проверка прогресса и скачивание checkpoint-ов.

## 1. Подключение к Vast

```bash
ssh -i ~/.ssh/vastai_key -p 44667 root@146.115.17.148 -L 8080:localhost:8080
```

Рабочая директория на Vast:

```bash
/root/cube-act
```

Python environment:

```bash
/root/cube-act/.venv
```

Активация:

```bash
cd /root/cube-act
source .venv/bin/activate
```

## 2. Первичная установка на Vast

Если репозитория еще нет:

```bash
cd /root
git clone https://github.com/ebulochkin/cube-act.git cube-act
cd /root/cube-act
```

Создать venv на Python 3.12:

```bash
uv venv .venv --python /usr/bin/python3
source .venv/bin/activate
```

Поставить LeRobot:

```bash
mkdir -p /root/code
git clone https://github.com/huggingface/lerobot.git /root/code/lerobot
cd /root/code/lerobot
uv pip install -e ".[core_scripts,training]"
uv pip install huggingface_hub hf_transfer
```

## 3. Скачать dataset

```bash
cd /root/cube-act
source .venv/bin/activate

mkdir -p cache/datasets/so101_cube_pick

HF_XET_HIGH_PERFORMANCE=1 hf download \
  ebulochkin/so101_cube_pick676767 \
  --repo-type dataset \
  --local-dir cache/datasets/so101_cube_pick
```

Dataset path:

```bash
/root/cube-act/cache/datasets/so101_cube_pick
```

## 4. Настроить config.env

```bash
cd /root/cube-act
cp -n config.env.example config.env
nano config.env
```

Финальные агрессивные параметры для A100:

```bash
DATASET_REPO_ID=ebulochkin/so101_cube_pick676767
DATASET_ROOT=cache/datasets/so101_cube_pick

TRAIN_STEPS=9250
TRAIN_BATCH_SIZE=104
TRAIN_NUM_WORKERS=8
TRAIN_PREFETCH_FACTOR=4
TRAIN_SAVE_FREQ=3000
TRAIN_POLICY_USE_AMP=true
TRAIN_DATASET_RETURN_UINT8=true
```

Если будет CUDA OOM, откатиться на:

```bash
TRAIN_STEPS=10000
TRAIN_BATCH_SIZE=96
```

или стабильнее:

```bash
TRAIN_STEPS=15000
TRAIN_BATCH_SIZE=64
```

## 5. Запуск training в tmux

```bash
cd /root/cube-act
source .venv/bin/activate
tmux new-session -s ssh_tmux
```

Внутри `tmux`:

```bash
./scripts/03_train_act.sh
```

Отцепиться от `tmux`, не останавливая обучение:

```text
Ctrl-b
d
```

Вернуться в `tmux`:

```bash
tmux attach -t ssh_tmux
```

Проверить процессы:

```bash
ps -ef | grep lerobot-train
```

Проверить GPU:

```bash
nvidia-smi
```

## 6. Где лежат результаты

Output dir:

```bash
/root/cube-act/outputs/train/so101_cube_act
```

Checkpoints:

```bash
/root/cube-act/outputs/train/so101_cube_act/checkpoints
```

Во время нашего запуска появились:

```text
003000
006000
009000
009250
```

Финальный checkpoint:

```bash
/root/cube-act/outputs/train/so101_cube_act/checkpoints/009250
```

Policy path для rollout/replay:

```bash
/root/cube-act/outputs/train/so101_cube_act/checkpoints/009250/pretrained_model
```

## 7. Скачать checkpoint локально

Команду ниже запускать с локальной машины, не внутри Vast:

```bash
mkdir -p /Users/tdbg/cube-act/remote_checkpoints

rsync -av --progress \
  -e 'ssh -i ~/.ssh/vastai_key -o IdentitiesOnly=yes -p 44667' \
  root@146.115.17.148:/root/cube-act/outputs/train/so101_cube_act/checkpoints/009250/ \
  /Users/tdbg/cube-act/remote_checkpoints/so101_cube_act_009250/
```

Локально checkpoint будет тут:

```bash
/Users/tdbg/cube-act/remote_checkpoints/so101_cube_act_009250
```

## 8. Скачать логи для графиков

```bash
mkdir -p /Users/tdbg/cube-act/remote_logs

rsync -av \
  -e 'ssh -i ~/.ssh/vastai_key -o IdentitiesOnly=yes -p 44667' \
  root@146.115.17.148:/root/cube-act/train.log \
  /Users/tdbg/cube-act/remote_logs/train.log
```

Сохранить `tmux` capture:

```bash
ssh -i ~/.ssh/vastai_key -p 44667 root@146.115.17.148 \
  'tmux capture-pane -t ssh_tmux -p -S -5000' \
  > /Users/tdbg/cube-act/remote_logs/ssh_tmux_training_capture.txt
```

У нас также был сделан CSV:

```bash
/Users/tdbg/cube-act/remote_logs/training_metrics_104.csv
```

Формат:

```csv
step,samples,epoch,loss,grad_norm
```

## 9. Итог нашего запуска

Финальный run:

```text
batch_size=104
steps=9250
save_freq=3000
training time ~2h 26m
final loss around 0.106
```

Финальный checkpoint:

```bash
/Users/tdbg/cube-act/remote_checkpoints/so101_cube_act_009250
```

Для проверки качества лучше сравнивать checkpoints через rollout/replay, а не только по loss. Обычно кандидаты:

```text
003000 - ранний
006000 - середина
009250 - финальный
```

