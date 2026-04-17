from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


DEFAULT_NRF_BAUD = 115200
DEFAULT_AT_TIMEOUT = 0.8
JLINK_VID = 0x1366


@dataclass(frozen=True)
class AtCommandResult:
    command: str
    lines: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return any(line == "OK" for line in self.lines)


@dataclass(frozen=True)
class NrfModemProbe:
    port: str
    at: AtCommandResult
    firmware: AtCommandResult

    @property
    def responds_to_at(self) -> bool:
        return self.at.ok

    @property
    def firmware_version(self) -> str:
        return parse_firmware_version(self.firmware.lines)

    @property
    def is_modem_port(self) -> bool:
        return self.responds_to_at and bool(self.firmware_version)


def clean_response_lines(raw: bytes | str) -> tuple[str, ...]:
    if isinstance(raw, bytes):
        text = raw.decode("utf-8", errors="replace")
    else:
        text = raw
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def parse_firmware_version(lines: Iterable[str]) -> str:
    for line in lines:
        if line == "OK" or line.startswith("AT"):
            continue
        if line.startswith("ERROR"):
            continue
        return line
    return ""


def candidate_nrf_ports() -> list[str]:
    from serial.tools import list_ports

    ports: list[str] = []
    for port in list_ports.comports():
        if port.vid == JLINK_VID or "J-Link" in (port.description or ""):
            ports.append(port.device)
    return ports


def send_at_command(device, command: str, timeout: float = DEFAULT_AT_TIMEOUT) -> AtCommandResult:
    import time

    device.reset_input_buffer()
    device.write((command + "\r\n").encode("ascii"))
    device.flush()
    time.sleep(timeout)
    raw = device.read(device.in_waiting or 256)
    return AtCommandResult(command=command, lines=clean_response_lines(raw))


def probe_nrf_modem_port(
    port: str,
    baud: int = DEFAULT_NRF_BAUD,
    timeout: float = DEFAULT_AT_TIMEOUT,
) -> NrfModemProbe:
    import serial
    import time

    with serial.Serial(port, baud, timeout=timeout, write_timeout=timeout) as device:
        time.sleep(timeout)
        device.read(device.in_waiting or 1)
        at = send_at_command(device, "AT", timeout)
        firmware = send_at_command(device, "AT+CGMR", timeout)

    return NrfModemProbe(port=port, at=at, firmware=firmware)
