from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any

import cv2
import numpy as np
from lerobot.cameras.camera import Camera
from lerobot.cameras.configs import CameraConfig, ColorMode
from lerobot.utils.errors import DeviceNotConnectedError
from lerobot.utils.import_utils import require_package
from numpy.typing import NDArray

try:
    import pyzed.sl as sl
except ImportError:
    sl = None

logger = logging.getLogger(__name__)

ZED_LOCK_PATTERNS = ("/tmp/.zed_enum_lock", "/tmp/.zed_*lock*")


@CameraConfig.register_subclass("zed")
@dataclass
class ZEDCameraConfig(CameraConfig):
    camera_name: str = "zed"
    zed_resolution: str = "HD720"
    color_mode: ColorMode = ColorMode.RGB
    warmup_frames: int = 60
    warmup_s: int = 1
    open_retries: int = 5
    open_retry_sleep_s: float = 2.0
    pre_open_sleep_s: float = 0.0
    auto_exposure: bool = True
    exposure: int = -1
    gain: int = -1
    led: bool = True

    def __post_init__(self) -> None:
        self.color_mode = ColorMode(self.color_mode)
        if self.fps is None:
            self.fps = 30
        if self.width is None:
            self.width = 640
        if self.height is None:
            self.height = 480
        if self.warmup_frames < 0:
            raise ValueError("warmup_frames must be non-negative")
        if self.open_retries < 1:
            raise ValueError("open_retries must be >= 1")
        if self.pre_open_sleep_s < 0:
            raise ValueError("pre_open_sleep_s must be non-negative")
        if self.exposure != -1 and not 0 <= self.exposure <= 100:
            raise ValueError("exposure must be in [0, 100], or -1")
        if self.gain != -1 and not 0 <= self.gain <= 100:
            raise ValueError("gain must be in [0, 100], or -1")


class ZEDCamera(Camera):
    def __init__(self, config: ZEDCameraConfig):
        require_package("pyzed", extra="zed", import_name="pyzed.sl")
        super().__init__(config)
        self.config = config
        self.color_mode = config.color_mode
        self.zed: sl.Camera | None = None
        self.runtime: sl.RuntimeParameters | None = None
        self.image: sl.Mat | None = None
        self.thread: Thread | None = None
        self.stop_event: Event | None = None
        self.frame_lock: Lock = Lock()
        self.latest_frame: NDArray[Any] | None = None
        self.latest_timestamp: float | None = None
        self.latest_sequence = 0
        self.last_read_sequence = 0

    def __str__(self) -> str:
        return f"ZEDCamera({self.config.camera_name})"

    @property
    def is_connected(self) -> bool:
        return self.zed is not None

    @staticmethod
    def find_cameras() -> list[dict[str, Any]]:
        return []

    def connect(self, warmup: bool = True) -> None:
        if self.is_connected:
            return

        if sl is None:
            raise ImportError("Stereolabs ZED Python API is not available: failed to import pyzed.sl")

        self._clear_zed_locks()

        init = sl.InitParameters()
        init.camera_resolution = getattr(sl.RESOLUTION, self.config.zed_resolution)
        init.camera_fps = int(self.fps or 30)
        init.depth_mode = sl.DEPTH_MODE.NONE
        init.coordinate_units = sl.UNIT.METER

        if self.config.pre_open_sleep_s:
            logger.info("Waiting %.1fs before opening %s", self.config.pre_open_sleep_s, self)
            time.sleep(self.config.pre_open_sleep_s)

        status = sl.ERROR_CODE.FAILURE
        zed: sl.Camera | None = None
        for attempt in range(1, self.config.open_retries + 1):
            logger.info(
                "Opening %s attempt %s/%s: resolution=%s fps=%s size=%sx%s",
                self,
                attempt,
                self.config.open_retries,
                self.config.zed_resolution,
                self.fps,
                self.width,
                self.height,
            )
            zed = sl.Camera()
            status = zed.open(init)
            if status == sl.ERROR_CODE.SUCCESS:
                break
            logger.warning(
                "Failed to open %s on attempt %s/%s: %s",
                self,
                attempt,
                self.config.open_retries,
                status,
            )
            try:
                zed.close()
            except Exception:
                pass
            zed = None
            if attempt < self.config.open_retries:
                time.sleep(self.config.open_retry_sleep_s)

        if status != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError(f"Failed to open {self} after {self.config.open_retries} attempts: {status}")

        if zed is None:
            raise RuntimeError(f"Failed to create {self}")

        self.zed = zed
        self.runtime = sl.RuntimeParameters()
        self.image = sl.Mat()

        if self.config.auto_exposure and hasattr(sl.VIDEO_SETTINGS, "AEC_AGC"):
            self.zed.set_camera_settings(sl.VIDEO_SETTINGS.AEC_AGC, 1)
        if self.config.exposure >= 0:
            self.zed.set_camera_settings(sl.VIDEO_SETTINGS.EXPOSURE, self.config.exposure)
        if self.config.gain >= 0:
            self.zed.set_camera_settings(sl.VIDEO_SETTINGS.GAIN, self.config.gain)
        if self.config.led and hasattr(sl.VIDEO_SETTINGS, "LED_STATUS"):
            self.zed.set_camera_settings(sl.VIDEO_SETTINGS.LED_STATUS, 1)

        for _ in range(self.config.warmup_frames):
            self.zed.grab(self.runtime)

        self._start_read_thread()

        if warmup:
            deadline = time.time() + max(self.config.warmup_s, 1)
            while time.time() < deadline:
                try:
                    self.async_read(timeout_ms=200)
                    return
                except TimeoutError:
                    pass
            raise TimeoutError(f"Timed out waiting for first frame from {self}")

    def _start_read_thread(self) -> None:
        self.stop_event = Event()
        self.thread = Thread(target=self._read_loop, daemon=True, name=f"{self}_read_loop")
        self.thread.start()

    def _read_loop(self) -> None:
        if self.stop_event is None or self.zed is None or self.runtime is None or self.image is None:
            return

        resolution = sl.Resolution(int(self.width or 640), int(self.height or 480))
        while not self.stop_event.is_set():
            status = self.zed.grab(self.runtime)
            if status != sl.ERROR_CODE.SUCCESS:
                time.sleep(0.005)
                continue

            self.zed.retrieve_image(self.image, sl.VIEW.LEFT, sl.MEM.CPU, resolution)
            bgra = self.image.get_data()
            frame = cv2.cvtColor(bgra, cv2.COLOR_BGRA2RGB)
            if self.color_mode == ColorMode.BGR:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            frame = np.ascontiguousarray(frame)

            with self.frame_lock:
                self.latest_frame = frame
                self.latest_timestamp = time.perf_counter()
                self.latest_sequence += 1

    def async_read(self, timeout_ms: float = 200) -> NDArray[Any]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected")

        deadline = time.perf_counter() + timeout_ms / 1000.0
        while time.perf_counter() < deadline:
            with self.frame_lock:
                frame = self.latest_frame
                sequence = self.latest_sequence

            if frame is not None:
                self.last_read_sequence = sequence
                return frame
            time.sleep(0.001)

        raise TimeoutError(f"Timed out waiting for frame from {self} after {timeout_ms} ms")

    def read(self) -> NDArray[Any]:
        return self.async_read(timeout_ms=10000)

    def read_latest(self, max_age_ms: int = 1000) -> NDArray[Any]:
        if not self.is_connected:
            raise DeviceNotConnectedError(f"{self} is not connected")

        with self.frame_lock:
            frame = self.latest_frame
            timestamp = self.latest_timestamp

        if frame is None or timestamp is None:
            raise RuntimeError(f"{self} has not captured any frames yet")

        age_ms = (time.perf_counter() - timestamp) * 1000
        if age_ms > max_age_ms:
            raise TimeoutError(f"{self} latest frame is too old: {age_ms:.1f} ms")

        return frame

    def disconnect(self) -> None:
        if self.stop_event is not None:
            self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=2.0)
        self.thread = None
        self.stop_event = None

        if self.zed is not None:
            self.zed.close()
        self.zed = None
        self.runtime = None
        self.image = None

        with self.frame_lock:
            self.latest_frame = None
            self.latest_timestamp = None
            self.latest_sequence = 0
            self.last_read_sequence = 0

    @staticmethod
    def _clear_zed_locks() -> None:
        for pattern in ZED_LOCK_PATTERNS:
            for lock_path in Path("/").glob(pattern.lstrip("/")):
                try:
                    os.remove(lock_path)
                    logger.info("Removed stale ZED lock file: %s", lock_path)
                except FileNotFoundError:
                    pass
                except PermissionError:
                    logger.warning("No permission to remove ZED lock file: %s", lock_path)
