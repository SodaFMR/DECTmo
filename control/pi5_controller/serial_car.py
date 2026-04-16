from __future__ import annotations

import time
from dataclasses import dataclass

import serial
from serial.tools import list_ports


DEFAULT_BAUD = 115200
DEFAULT_PULSE_MS = 250
READ_IDLE_SECONDS = 0.08


class SerialCarError(RuntimeError):
    pass


def find_pico_port(preferred_port: str | None = None) -> str:
    if preferred_port:
        return preferred_port

    ports = list(list_ports.comports())
    if not ports:
        raise SerialCarError("No serial ports found. Is the Pico connected over USB?")

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


@dataclass(frozen=True)
class MoveCommand:
    command: str
    speed: int
    duration_ms: int

    def encode(self) -> bytes:
        return f"{self.command} {self.speed} {self.duration_ms}\n".encode("ascii")


class SerialCar:
    def __init__(
        self,
        port: str | None = None,
        baud: int = DEFAULT_BAUD,
        startup_delay: float = 1.8,
    ) -> None:
        self.port = find_pico_port(port)
        self.baud = baud
        self.startup_delay = startup_delay
        self.serial: serial.Serial | None = None

    def __enter__(self) -> "SerialCar":
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

    def send_line(self, line: str) -> None:
        if self.serial is None:
            raise SerialCarError("Serial connection is not open.")
        payload = line.rstrip("\r\n").encode("ascii") + b"\n"
        self.serial.write(payload)
        self.serial.flush()

    def send_move(self, action: str, speed: int, duration_ms: int, wheel_mode: str) -> None:
        self._validate_speed(speed)
        action_key = action.lower()
        command = self._command_for_action(action_key, wheel_mode)
        if command == "S":
            self.stop()
            return
        self._write_move(MoveCommand(command, speed, duration_ms))

    def stop(self) -> None:
        self.send_line("S")

    def ping(self) -> str:
        if self.serial is None:
            raise SerialCarError("Serial connection is not open.")
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
            raise SerialCarError("Serial connection is not open.")
        self.read_available_lines()
        self.send_line("INFO")
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            response = self.serial.readline().decode("utf-8", errors="replace").strip()
            if not response:
                continue
            if response.startswith("INFO "):
                return self._parse_info(response)
        return {}

    def read_available_lines(self) -> list[str]:
        if self.serial is None:
            raise SerialCarError("Serial connection is not open.")
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

    def _write_move(self, command: MoveCommand) -> None:
        if self.serial is None:
            raise SerialCarError("Serial connection is not open.")
        self.serial.write(command.encode())
        self.serial.flush()

    @staticmethod
    def _command_for_action(action: str, wheel_mode: str) -> str:
        if action == "forward":
            return "F"
        if action == "backward":
            return "B"
        if action == "left":
            return "ML" if wheel_mode == "mecanum" else "L"
        if action == "right":
            return "MR" if wheel_mode == "mecanum" else "R"
        if action == "stop":
            return "S"
        raise SerialCarError(f"Unsupported action: {action}")

    @staticmethod
    def _validate_speed(speed: int) -> None:
        if speed < 0 or speed > 100:
            raise SerialCarError("Speed must be between 0 and 100.")

    @staticmethod
    def _parse_info(line: str) -> dict[str, str]:
        info: dict[str, str] = {}
        for item in line.removeprefix("INFO ").split():
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            info[key] = value
        return info
