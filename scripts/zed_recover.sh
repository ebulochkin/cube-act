#!/usr/bin/env bash
set -euo pipefail

echo "Stopping processes that may hold the ZED camera..."
pkill -f zed2_zmq_publisher.py 2>/dev/null || true
pkill -f ZED_Explorer 2>/dev/null || true
pkill -f ZED_Depth_Viewer 2>/dev/null || true
pkill -f ZED_Diagnostic 2>/dev/null || true

echo "Removing stale ZED lock files..."
rm -f /tmp/.zed_enum_lock /tmp/.zed_*lock* 2>/dev/null || true

echo "Waiting for the SDK/USB stack to release the device..."
sleep 5

echo "Remaining ZED-related processes:"
ps aux | grep -E "zed2_zmq|ZED_|pyzed" | grep -v grep || true

echo
echo "Video devices by id:"
ls -l /dev/v4l/by-id 2>/dev/null || true

echo
echo "Done. If ZED still does not open, unplug/replug the ZED USB cable and run this script again."
