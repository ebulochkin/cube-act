#!/usr/bin/env python3
"""Publish ZED 2 RGB frames using LeRobot's ZMQ camera JSON protocol."""

from __future__ import annotations

import argparse
import base64
import contextlib
import json
import logging
import signal
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.fps <= 0:
        raise SystemExit("--fps must be positive")
    if args.width <= 0 or args.height <= 0:
        raise SystemExit("--width and --height must be positive")
    if not 1 <= args.jpeg_quality <= 100:
        raise SystemExit("--jpeg-quality must be in [1, 100]")

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
    status = zed.open(init)
    if status != sl.ERROR_CODE.SUCCESS:
        raise SystemExit(f"Failed to open ZED 2: {status}")

    runtime = sl.RuntimeParameters()
    image = sl.Mat()

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.setsockopt(zmq.SNDHWM, 20)
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
    saved_first_frame = False

    try:
        while running:
            start = time.perf_counter()
            if zed.grab(runtime) == sl.ERROR_CODE.SUCCESS:
                zed.retrieve_image(image, sl.VIEW.LEFT, sl.MEM.CPU, sl.Resolution(args.width, args.height))
                rgba = image.get_data()
                rgb = cv2.cvtColor(rgba, cv2.COLOR_RGBA2RGB)

                frame_count += 1
                now = time.time()
                if args.debug_stats and now - last_stats_t >= 1.0:
                    logging.info(
                        "ZED frame stats: shape=%s dtype=%s min=%s max=%s mean=%.2f",
                        rgb.shape,
                        rgb.dtype,
                        int(rgb.min()),
                        int(rgb.max()),
                        float(rgb.mean()),
                    )
                    last_stats_t = now

                if args.save_first_frame and not saved_first_frame:
                    cv2.imwrite(args.save_first_frame, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                    logging.info("Saved first ZED frame to %s", args.save_first_frame)
                    saved_first_frame = True

                payload = {
                    "timestamps": {args.camera_name: now},
                    "images": {args.camera_name: encode_image_rgb(rgb, args.jpeg_quality)},
                }
                with contextlib.suppress(zmq.Again):
                    socket.send_string(json.dumps(payload), flags=zmq.NOBLOCK)

            elapsed = time.perf_counter() - start
            if elapsed < frame_period_s:
                time.sleep(frame_period_s - elapsed)
    finally:
        socket.close()
        context.term()
        zed.close()


if __name__ == "__main__":
    main()
