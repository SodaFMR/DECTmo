from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import serial
from serial.tools import list_ports


DEFAULT_BAUD = 115200
DEFAULT_SPEED = 50
DEFAULT_DURATION_MS = 250
DEFAULT_WHEEL_MODE = "ordinary"
ORDINARY_TURN_REVERSE_SPEED = 28
READ_IDLE_SECONDS = 0.08

MOVE_ACTIONS = {"forward", "backward", "left", "right"}
ACTIONS = MOVE_ACTIONS | {"stop"}
WHEEL_MODES = {"ordinary", "mecanum"}


class CarError(RuntimeError):
    pass


def normalize_action(action: str) -> str:
    aliases = {
        "w": "forward",
        "f": "forward",
        "s": "stop",
        "b": "backward",
        "back": "backward",
        "backwards": "backward",
        "a": "left",
        "l": "left",
        "d": "right",
        "r": "right",
    }
    key = str(action).strip().lower()
    return aliases.get(key, key)


@dataclass(frozen=True)
class Movement:
    action: str
    duration_ms: int = DEFAULT_DURATION_MS
    speed: int = DEFAULT_SPEED

    @classmethod
    def from_dict(
        cls,
        payload: dict[str, Any],
        default_speed: int = DEFAULT_SPEED,
        default_duration_ms: int = DEFAULT_DURATION_MS,
    ) -> "Movement":
        action = str(payload.get("action", "stop"))
        duration_ms = int(payload.get("duration_ms", payload.get("duration", default_duration_ms)))
        speed = int(payload.get("speed", default_speed))
        return cls(action=action, duration_ms=duration_ms, speed=speed).normalized()

    def normalized(self) -> "Movement":
        action = normalize_action(self.action)
        if action not in ACTIONS:
            raise CarError(f"Unsupported movement action: {self.action}")

        speed = int(self.speed)
        duration_ms = int(self.duration_ms)
        if not 0 <= speed <= 100:
            raise CarError("Speed must be between 0 and 100.")
        if not 0 <= duration_ms <= 5000:
            raise CarError("duration_ms must be between 0 and 5000.")
        if action in MOVE_ACTIONS and speed == 0:
            raise CarError("Movement actions require speed greater than 0.")
        if action == "stop":
            speed = 0

        return Movement(action=action, speed=speed, duration_ms=duration_ms)

    def to_dict(self) -> dict[str, int | str]:
        return {
            "action": self.action,
            "speed": self.speed,
            "duration_ms": self.duration_ms,
        }


def find_pico_port(preferred_port: str | None = None) -> str:
    if preferred_port:
        return preferred_port

    ports = list(list_ports.comports())
    if not ports:
        raise CarError("No serial ports found. Is the Pico connected over USB?")

    pico_vid = 0x2E8A
    for port in ports:
        if port.vid == pico_vid:
            return port.device

    for port in ports:
        text = " ".join(
            part for part in (port.device, port.description, port.manufacturer) if part
        ).lower()
        if "pico" in text or "rp2040" in text:
            return port.device

    for port in ports:
        if port.device.startswith("/dev/ttyACM") or port.device.startswith("/dev/ttyUSB"):
            return port.device

    return ports[0].device


def build_pico_line(movement: Movement, wheel_mode: str = DEFAULT_WHEEL_MODE) -> str:
    movement = movement.normalized()
    mode = wheel_mode.strip().lower()
    if mode not in WHEEL_MODES:
        raise CarError(f"Unsupported wheel mode: {wheel_mode}")

    if movement.action == "stop":
        return "S"
    if movement.action == "forward":
        return f"F {movement.speed} {movement.duration_ms}"
    if movement.action == "backward":
        return f"B {movement.speed} {movement.duration_ms}"
    if mode == "mecanum":
        if movement.action == "left":
            return f"ML {movement.speed} {movement.duration_ms}"
        if movement.action == "right":
            return f"MR {movement.speed} {movement.duration_ms}"

    reverse_speed = ordinary_turn_reverse_speed(movement.speed)
    if movement.action == "left":
        return f"DRIVE -{reverse_speed} {movement.speed} {movement.duration_ms}"
    if movement.action == "right":
        return f"DRIVE {movement.speed} -{reverse_speed} {movement.duration_ms}"

    raise CarError(f"Unsupported movement action: {movement.action}")


def ordinary_turn_reverse_speed(speed: int) -> int:
    if speed <= 0:
        return 0
    return min(speed, ORDINARY_TURN_REVERSE_SPEED)


class Car:
    def __init__(
        self,
        port: str | None = None,
        baud: int = DEFAULT_BAUD,
        wheel_mode: str = DEFAULT_WHEEL_MODE,
        startup_delay: float = 1.8,
    ) -> None:
        self.port = find_pico_port(port)
        self.baud = baud
        self.wheel_mode = wheel_mode
        self.startup_delay = startup_delay
        self.serial: serial.Serial | None = None

    def __enter__(self) -> "Car":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self) -> None:
        self.serial = serial.Serial(
            self.port,
            self.baud,
            timeout=0.2,
            write_timeout=0.2,
        )
        time.sleep(self.startup_delay)
        self.serial.reset_input_buffer()
        self.stop()
        time.sleep(READ_IDLE_SECONDS)
        self.read_available_lines()

    def close(self) -> None:
        if self.serial is None:
            return
        try:
            self.stop()
        finally:
            self.serial.close()
            self.serial = None

    def send_move(
        self,
        action: str,
        duration_ms: int = DEFAULT_DURATION_MS,
        speed: int = DEFAULT_SPEED,
    ) -> Movement:
        movement = Movement(action=action, duration_ms=duration_ms, speed=speed).normalized()
        self.send_line(build_pico_line(movement, self.wheel_mode))
        return movement

    def stop(self) -> Movement:
        self.send_line("S")
        return Movement(action="stop", duration_ms=0, speed=0)

    def send_line(self, line: str) -> None:
        if self.serial is None:
            raise CarError("Serial connection is not open.")
        payload = line.rstrip("\r\n").encode("ascii") + b"\n"
        self.serial.write(payload)
        self.serial.flush()

    def ping(self) -> str:
        if self.serial is None:
            raise CarError("Serial connection is not open.")
        self.read_available_lines()
        self.send_line("PING")
        deadline = time.monotonic() + 1.0
        lines: list[str] = []
        while time.monotonic() < deadline:
            response = self.serial.readline().decode("utf-8", errors="replace").strip()
            if not response:
                continue
            lines.append(response)
            if response == "PONG":
                return response
        return lines[-1] if lines else ""

    def info(self) -> dict[str, str]:
        if self.serial is None:
            raise CarError("Serial connection is not open.")
        self.read_available_lines()
        self.send_line("INFO")
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            response = self.serial.readline().decode("utf-8", errors="replace").strip()
            if response.startswith("INFO "):
                return self._parse_info(response)
        return {}

    def read_available_lines(self) -> list[str]:
        if self.serial is None:
            raise CarError("Serial connection is not open.")
        lines: list[str] = []
        deadline = time.monotonic() + READ_IDLE_SECONDS
        while time.monotonic() < deadline:
            if self.serial.in_waiting == 0:
                time.sleep(0.01)
                continue
            line = self.serial.readline().decode("utf-8", errors="replace").strip()
            if line:
                lines.append(line)
                deadline = time.monotonic() + READ_IDLE_SECONDS
        return lines

    @staticmethod
    def _parse_info(line: str) -> dict[str, str]:
        info: dict[str, str] = {}
        for item in line.removeprefix("INFO ").split():
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            info[key] = value
        return info
