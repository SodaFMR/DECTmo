from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path


class CameraError(RuntimeError):
    pass


@dataclass(frozen=True)
class CameraConfig:
    device: str = "/dev/video0"
    width: int = 640
    height: int = 480
    fps: int = 15
    quality: int = 80


def list_video_devices() -> list[str]:
    return sorted(str(path) for path in Path("/dev").glob("video*"))


def describe_v4l2_devices() -> str:
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "v4l2-ctl is not installed. Install it with: sudo apt install -y v4l-utils"

    output = result.stdout.strip() or result.stderr.strip()
    return output or "v4l2-ctl returned no device details."


class UsbCamera:
    def __init__(self, config: CameraConfig) -> None:
        self.config = config
        self._lock = threading.Lock()
        self._cv2 = None
        self._capture = None
        self.last_error = ""

    @property
    def enabled(self) -> bool:
        return self.config.device.lower() not in {"", "none", "off", "disabled"}

    def open(self) -> None:
        if not self.enabled:
            raise CameraError("Camera is disabled.")
        if self._capture is not None:
            return

        try:
            import cv2
        except ImportError as exc:
            raise CameraError(
                "OpenCV is required for USB camera streaming. "
                "Install it with: sudo apt install -y python3-opencv v4l-utils"
            ) from exc

        device_ref: str | int = self.config.device
        if self.config.device.isdigit():
            device_ref = int(self.config.device)

        capture = cv2.VideoCapture(device_ref, cv2.CAP_V4L2)
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        capture.set(cv2.CAP_PROP_FPS, self.config.fps)

        if not capture.isOpened():
            capture.release()
            raise CameraError(f"Could not open camera device {self.config.device}.")

        self._cv2 = cv2
        self._capture = capture

    def read_jpeg(self) -> bytes | None:
        if not self.enabled:
            self.last_error = "Camera is disabled."
            return None

        with self._lock:
            try:
                self.open()
                ok, frame = self._capture.read()
                if not ok:
                    self.last_error = f"Camera read failed on {self.config.device}."
                    return None

                encode_params = [self._cv2.IMWRITE_JPEG_QUALITY, self.config.quality]
                ok, encoded = self._cv2.imencode(".jpg", frame, encode_params)
                if not ok:
                    self.last_error = "JPEG encoding failed."
                    return None

                self.last_error = ""
                return encoded.tobytes()
            except CameraError as exc:
                self.last_error = str(exc)
                return None

    def close(self) -> None:
        with self._lock:
            if self._capture is not None:
                self._capture.release()
                self._capture = None

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "device": self.config.device,
            "active": self._capture is not None,
            "last_error": self.last_error,
        }
