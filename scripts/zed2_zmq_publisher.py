#!/usr/bin/env python3
"""Publish ZED 2 RGB frames using LeRobot's ZMQ camera JSON protocol."""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import logging
import signal
import threading
import time

import cv2
import numpy as np
import zmq

try:
    import pyzed.sl as sl
except ImportError as exc:
    try:
        import pyzed

        pyzed_location = getattr(pyzed, "__file__", "unknown location")
    except ImportError:
        pyzed_location = "not importable at all"

    raise SystemExit(
        "Stereolabs ZED Python API is not available: failed to import `pyzed.sl`.\n"
        f"Current `pyzed` resolves to: {pyzed_location}\n"
        "The PyPI package named `pyzed` is not enough for ZED cameras.\n"
        "If `pyzed` resolves to a single `pyzed.py` file, remove it with:\n"
        "  pip uninstall -y pyzed\n"
        "Install the ZED SDK, then run its Python installer in this environment, usually:\n"
        "  cd /usr/local/zed && python get_python_api.py\n"
        "Check with:\n"
        "  python -c \"import pyzed.sl as sl; print('pyzed.sl ok')\""
    ) from exc


RESOLUTIONS = {
    "HD2K": sl.RESOLUTION.HD2K,
    "HD1080": sl.RESOLUTION.HD1080,
    "HD720": sl.RESOLUTION.HD720,
    "VGA": sl.RESOLUTION.VGA,
}


def encode_image_rgb(image: np.ndarray, quality: int) -> str:
    ok, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("Failed to JPEG-encode ZED frame")
    return base64.b64encode(buffer).decode("utf-8")


class ZEDCaptureThread:
    def __init__(self, zed: sl.Camera, runtime: sl.RuntimeParameters, width: int, height: int):
        self.zed = zed
        self.runtime = runtime
        self.width = width
        self.height = height
        self.image = sl.Mat()
        self.lock = threading.Lock()
        self.running = False
        self.thread: threading.Thread | None = None
        self.latest_frame: np.ndarray | None = None
        self.latest_timestamp = 0.0
        self.latest_sequence = 0
        self.failures = 0

    def start(self) -> None:
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="zed_capture")
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2.0)

    def get_latest(self) -> tuple[np.ndarray | None, float, int]:
        with self.lock:
            frame = None if self.latest_frame is None else self.latest_frame.copy()
            return frame, self.latest_timestamp, self.latest_sequence

    def _loop(self) -> None:
        resolution = sl.Resolution(self.width, self.height)
        while self.running:
            status = self.zed.grab(self.runtime)
            if status != sl.ERROR_CODE.SUCCESS:
                self.failures += 1
                time.sleep(0.005)
                continue

            self.zed.retrieve_image(self.image, sl.VIEW.LEFT, sl.MEM.CPU, resolution)
            rgba = self.image.get_data()
            rgb = cv2.cvtColor(rgba, cv2.COLOR_RGBA2RGB).copy()
            now = time.time()

            with self.lock:
                self.latest_frame = rgb
                self.latest_timestamp = now
                self.latest_sequence += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=5555)
    parser.add_argument("--camera-name", default="overhead")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--resolution", choices=RESOLUTIONS, default="HD720")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--jpeg-quality", type=int, default=80)
    parser.add_argument("--depth-mode", choices=["none", "performance", "quality"], default="none")
    parser.add_argument("--debug-stats", action="store_true", help="Log frame pixel statistics once per second.")
    parser.add_argument("--save-first-frame", help="Write the first captured RGB frame to this image path.")
    parser.add_argument("--warmup-frames", type=int, default=60)
    parser.add_argument("--open-retries", type=int, default=5)
    parser.add_argument("--open-retry-sleep-s", type=float, default=2.0)
    parser.add_argument("--auto-exposure", action="store_true", help="Enable ZED auto exposure/gain when supported.")
    parser.add_argument("--exposure", type=int, default=-1, help="Manual exposure in [0, 100], or -1 to leave unchanged.")
    parser.add_argument("--gain", type=int, default=-1, help="Manual gain in [0, 100], or -1 to leave unchanged.")
    parser.add_argument("--led", action="store_true", help="Turn on ZED LED/status light when supported.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        raise SystemExit("--fps must be positive")
    if args.width <= 0 or args.height <= 0:
        raise SystemExit("--width and --height must be positive")
    if not 1 <= args.jpeg_quality <= 100:
        raise SystemExit("--jpeg-quality must be in [1, 100]")
    if args.warmup_frames < 0:
        raise SystemExit("--warmup-frames must be non-negative")
    if args.open_retries < 1:
        raise SystemExit("--open-retries must be >= 1")
    if args.open_retry_sleep_s < 0:
        raise SystemExit("--open-retry-sleep-s must be non-negative")
    if args.exposure != -1 and not 0 <= args.exposure <= 100:
        raise SystemExit("--exposure must be in [0, 100], or -1")
    if args.gain != -1 and not 0 <= args.gain <= 100:
        raise SystemExit("--gain must be in [0, 100], or -1")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    init = sl.InitParameters()
    init.camera_resolution = RESOLUTIONS[args.resolution]
    init.camera_fps = args.fps
    init.depth_mode = {
        "none": sl.DEPTH_MODE.NONE,
        "performance": sl.DEPTH_MODE.PERFORMANCE,
        "quality": sl.DEPTH_MODE.QUALITY,
    }[args.depth_mode]
    init.coordinate_units = sl.UNIT.METER

    zed = sl.Camera()
    status = sl.ERROR_CODE.FAILURE
    for attempt in range(1, args.open_retries + 1):
        status = zed.open(init)
        if status == sl.ERROR_CODE.SUCCESS:
            break

        logging.warning(
            "Failed to open ZED 2 on attempt %s/%s: %s",
            attempt,
            args.open_retries,
            status,
        )
        with contextlib.suppress(Exception):
            zed.close()
        if attempt < args.open_retries:
            time.sleep(args.open_retry_sleep_s)

    if status != sl.ERROR_CODE.SUCCESS:
        raise SystemExit(
            f"Failed to open ZED 2 after {args.open_retries} attempts: {status}\n"
            "Close ZED Explorer/other camera processes, wait a few seconds, or replug the camera."
        )

    if args.auto_exposure and hasattr(sl.VIDEO_SETTINGS, "AEC_AGC"):
        zed.set_camera_settings(sl.VIDEO_SETTINGS.AEC_AGC, 1)
        logging.info("Enabled ZED auto exposure/gain")
    if args.exposure >= 0:
        zed.set_camera_settings(sl.VIDEO_SETTINGS.EXPOSURE, args.exposure)
        logging.info("Set ZED exposure to %s", args.exposure)
    if args.gain >= 0:
        zed.set_camera_settings(sl.VIDEO_SETTINGS.GAIN, args.gain)
        logging.info("Set ZED gain to %s", args.gain)
    if args.led and hasattr(sl.VIDEO_SETTINGS, "LED_STATUS"):
        zed.set_camera_settings(sl.VIDEO_SETTINGS.LED_STATUS, 1)
        logging.info("Enabled ZED LED/status light")

    runtime = sl.RuntimeParameters()
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.setsockopt(zmq.SNDHWM, 1)
    socket.setsockopt(zmq.LINGER, 0)
    socket.bind(f"tcp://*:{args.port}")

    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    logging.info(
        "Publishing ZED 2 camera '%s' on tcp://*:%s at %sx%s@%s",
        args.camera_name,
        args.port,
        args.width,
        args.height,
        args.fps,
    )
    frame_period_s = 1.0 / args.fps
    frame_count = 0
    last_stats_t = 0.0
    last_report_t = time.time()
    saved_first_frame = False
    last_published_sequence = 0

    if args.warmup_frames:
        logging.info("Warming up ZED for %s frames before publishing", args.warmup_frames)
        for _ in range(args.warmup_frames):
            zed.grab(runtime)

    capture = ZEDCaptureThread(zed, runtime, args.width, args.height)
    capture.start()

    try:
        while running:
            start = time.perf_counter()
            rgb, capture_timestamp, sequence = capture.get_latest()
            if rgb is None or sequence == last_published_sequence:
                time.sleep(0.001)
                continue

            last_published_sequence = sequence
            frame_count += 1
            now = time.time()

            if args.debug_stats and now - last_stats_t >= 1.0:
                elapsed = max(now - last_report_t, 1e-9)
                logging.info(
                    "ZED frame stats: shape=%s dtype=%s min=%s max=%s mean=%.2f publish_fps=%.1f capture_failures=%s",
                    rgb.shape,
                    rgb.dtype,
                    int(rgb.min()),
                    int(rgb.max()),
                    float(rgb.mean()),
                    frame_count / elapsed,
                    capture.failures,
                )
                frame_count = 0
                last_report_t = now
                last_stats_t = now

            if args.save_first_frame and not saved_first_frame:
                cv2.imwrite(args.save_first_frame, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                logging.info("Saved first ZED frame to %s", args.save_first_frame)
                saved_first_frame = True

            payload = {
                "timestamps": {args.camera_name: capture_timestamp},
                "images": {args.camera_name: encode_image_rgb(rgb, args.jpeg_quality)},
            }
            with contextlib.suppress(zmq.Again):
                socket.send_string(json.dumps(payload), flags=zmq.NOBLOCK)

            elapsed = time.perf_counter() - start
            if elapsed < frame_period_s:
                time.sleep(frame_period_s - elapsed)
    finally:
        capture.stop()
        socket.close()
        context.term()
        zed.close()


if __name__ == "__main__":
    main()
