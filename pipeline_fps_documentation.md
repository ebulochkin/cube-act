# Dora-RS Pipeline: Архитектура и решение проблем с FPS

## Обзор архитектуры

Пайплайн записи датасета построен на фреймворке **Dora-RS** — распределённой системе,
где каждый узел (node) работает независимо и обменивается данными через Apache Arrow
без копирования (Zero-Copy IPC через shared memory).

```
dataflow_teleop_record.yml  ← главный оркестратор
```

### Граф узлов

```
dora/timer/millis/33 ──► cam_zed ──► encoder_zed ──► dora-record
                    ──► cam_rs_d435i ──► encoder_rs_d435i ──┘
                    ──► cam_rs_d405 ──► encoder_rs_d405 ───┘
                    ──► lerobot-dashboard (pygame UI)

leader-robot ──► teleop-mapper ──► follower-robot
                             ──► logical_action ──► dora-record
                             ──► logical_position ──► dora-record
```

---

## Проблема 1: ZED давала 13–19 FPS вместо 30

### Причина №1 — блокировка event loop

`camera_node.py` работает в event loop Dora по тикам `dora/timer/millis/33`.
На каждый тик вызывался `cam.read()` → `zed.grab()`.

**`zed.grab()` — блокирующий вызов**: он ждёт следующий кадр от USB (~33ms).
К этому добавлялся overhead IPC Dora (~20ms).
Итого `read()` занимал **53ms вместо 33ms = 19 FPS**.

```
Dora tick (33ms) → cam.read() → zed.grab() [блокировка 33ms] → retrieve_image [0.4ms]
                                             ↑
                              + IPC overhead ~20ms
                              = 53ms суммарно → 19 FPS
```

### Причина №2 — non-contiguous array

Старый `get_left()` возвращал `data[:,:,:3]` — **non-contiguous view** BGRA массива
со stride `[5120, 4, 1]`. При `frame.flatten()` numpy копировал попиксельно
с cache miss → ещё +30-50ms на кадр.

### Фикс: фоновый поток `_grab_loop`

**Ключевое решение в `src/cameras/zed_sdk_camera.py`:**

```python
class ZEDSDKCamera:
    def connect(self):
        # ...открываем ZED...
        self._running = True
        # Фоновый поток крутит grab() независимо от Dora
        self._thread = threading.Thread(target=self._grab_loop, daemon=True)
        self._thread.start()

    def _grab_loop(self):
        """
        КЛЮЧЕВОЙ МЕТОД: работает независимо от event loop Dora.
        Постоянно захватывает кадры с максимальной скоростью SDK.
        ZED SDK при DEPTH_MODE.NONE стабильно даёт 29-30 FPS.
        """
        img = sl.Mat()
        while self._running:
            if self.zed.grab(self.runtime_params) == sl.ERROR_CODE.SUCCESS:
                self.zed.retrieve_image(img, sl.VIEW.LEFT)
                data = img.get_data()
                if data is not None and len(data.shape) == 3:
                    # cv2.cvtColor возвращает CONTIGUOUS BGR массив.
                    # Без этого: data[:,:,:3] = non-contiguous view,
                    # flatten() копирует попиксельно = +30-50ms.
                    frame = cv2.cvtColor(data, cv2.COLOR_BGRA2BGR)
                    # Кроп лишнего фона (рейки конструкции)
                    frame = frame[140:590, 140:1140]
                    with self._lock:
                        self._left_frame = frame  # атомарная запись
            else:
                time.sleep(0.001)
        # os._exit минует деструкторы ZED SDK (иначе SIGSEGV при завершении)
        os._exit(0)

    def get_left(self):
        """Неблокирующее чтение последнего кадра — 0.4ms вместо 53ms."""
        with self._lock:
            return self._left_frame.copy() if self._left_frame is not None else None
```

**Результат:**

| Метрика | До | После |
|---|---|---|
| `cam.read()` | 53ms | 0.4ms |
| ZED FPS | 13-19 | **30** |

---

## Проблема 2: RealSense давала ~27 FPS (нестабильно)

### Причина — та же: блокировка в event loop

`pipeline.wait_for_frames(timeout_ms=5000)` блокировал основной поток на 35ms.
При нагрузке от других узлов Dora это добавляло jitter.

### Фикс: аналогичный фоновый поток

**`src/cameras/realsense_sdk_camera.py`:**

```python
def _grab_loop(self):
    """
    Фоновый поток для RealSense — тот же паттерн что и ZED.
    wait_for_frames с коротким timeout (200ms) чтобы поток
    реагировал на self._running = False в течение 0.2с.
    """
    while self._running:
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=200)
            color_frame = frames.get_color_frame()
            if color_frame:
                # np.asanyarray уже возвращает contiguous BGR массив
                # (librealsense конфигурирован на rs.format.bgr8)
                frame = np.asanyarray(color_frame.get_data())
                with self._lock:
                    self._latest_frame = frame
        except Exception:
            time.sleep(0.001)

def read(self):
    """Неблокирующее чтение — 0.2ms."""
    if not self.is_connected:
        return None
    with self._lock:
        return self._latest_frame.copy() if self._latest_frame is not None else None
```

**Результат:** D435i: 30 FPS, D405: 27-28 FPS (физическое ограничение USB bandwidth).

---

## Проблема 3: Видео ускорено при воспроизведении

### Причина — несоответствие реального FPS и FPS в заголовке mp4

Энкодер получал N кадров за T секунд реального времени, но собирал их
в mp4 с **фиксированным `r=FPS`** в ffmpeg:

```python
# node-hub/video-encoder/video_encoder/main.py
ffmpeg = (
    FFmpeg()
    .input(str(out_dir / "frame_%06d.jpg"), f="image2", r=fps)  # ← константа
    .output(str(video_path), vcodec="libx264", g=2, pix_fmt="yuv420p")
)
```

Если ZED давала 13 кадров за 27 секунд реального эпизода,
но энкодер собирал их с `r=30`, итоговый mp4 длился `13/30 = 0.43с` вместо 27с.
**Ускорение в 63 раза.**

### Фикс — устранили блокировки, обеспечив реальные 30 FPS

После устранения причин в _grab_loop камеры стали давать честные 30 FPS,
и видео перестало ускоряться.

Дополнительные исправления в энкодере:
- `pix_fmt="yuv444p"` → **`yuv420p`** (стандарт для VLA датасетов, совместим с torchvision)
- `PNG` → **`JPEG quality=95`** (~8x быстрее сжатие, снижает нагрузку на CPU)

---

## Проблема 4: Цветовые артефакты (синие лица на ZED)

### Причина — неправильная конвертация цветового пространства

Старый адаптер делал `cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)`,
а `cv2.imwrite()` в энкодере ожидает **BGR**.
Итог: R и B каналы менялись местами → синие лица, оранжевое небо.

### Фикс — единый BGR стандарт по всему пайплайну

```
ZED SDK (BGRA) → cvtColor(BGRA→BGR) → camera_node → encoder → cv2.imwrite(BGR) ✓
RealSense (BGR8) ───────────────────→ camera_node → encoder → cv2.imwrite(BGR) ✓
```

Конвертация в RGB нужна только потребителю (SmolVLA loader) — не в узле камеры.

---

## Проблема 5: ZED не открывается при повторном запуске

### Причина — lock файл `/tmp/.zed_enum_lock`

ZED SDK при падении (в т.ч. SIGSEGV при завершении) оставлял lock файл.
Следующий `zed.open()` видел его и отказывался открывать камеру.

### Фикс в `run_pipeline.sh`

```bash
# Очищаем lock файл ZED перед каждым запуском
rm -f /tmp/.zed_enum_lock /tmp/.zed_*lock* 2>/dev/null
```

---

## Итоговые цифры

```
                     До фикса    После фикса
─────────────────────────────────────────────
ZED cam.read()         53ms  →   0.4ms  (-99%)
RS  cam.read()         36ms  →   0.2ms  (-99%)
ZED FPS                 13   →    30    (+131%)
RS D435i FPS            30   →    30    (стабильно)
RS D405 FPS             27   →    28    (физ. лимит USB)
JPEG vs PNG (encoder)  40ms  →   5ms    (-88%)
```

---

## Структура файлов

```
src/
├── camera_node.py              # Dora-узел: lazy connect + профилировка
└── cameras/
    ├── zed_sdk_camera.py       # ZED: фоновый поток _grab_loop
    ├── lerobot_zed_camera.py   # Адаптер ZED → LeRobot интерфейс
    ├── zed_lerobot_factory.py  # Фабрика (синглтон ZEDSDKCamera)
    ├── realsense_sdk_camera.py # RealSense: фоновый поток _grab_loop
    └── realsense_lerobot_factory.py

node-hub/
└── video-encoder/
    └── video_encoder/main.py   # Encoder: JPEG + yuv420p

dataflow_teleop_record.yml      # Граф Dora (полные пути к бинарникам venv)
run_pipeline.sh                 # Запуск: очистка lock + активация venv
```
