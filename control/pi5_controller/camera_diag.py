from __future__ import annotations

import argparse
from pathlib import Path

from camera_stream import CameraConfig, UsbCamera, describe_v4l2_devices, list_video_devices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose a USB camera on the Pi 5.")
    parser.add_argument("--device", default="/dev/video0")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=15)
    parser.add_argument("--quality", type=int, default=80)
    parser.add_argument("--save", type=Path, default=Path("/tmp/dectmo_camera_test.jpg"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("Video nodes:")
    devices = list_video_devices()
    if devices:
        for device in devices:
            print(f"  {device}")
    else:
        print("  none")

    print("\nv4l2 devices:")
    print(describe_v4l2_devices())

    camera = UsbCamera(
        CameraConfig(
            device=args.device,
            width=args.width,
            height=args.height,
            fps=args.fps,
            quality=args.quality,
        )
    )

    frame = camera.read_jpeg()
    camera.close()
    if frame is None:
        print(f"\nCamera test failed: {camera.last_error}")
        return 1

    args.save.write_bytes(frame)
    print(f"\nCaptured {len(frame)} bytes from {args.device}")
    print(f"Saved test frame to {args.save}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
