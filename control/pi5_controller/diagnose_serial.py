from __future__ import annotations

import argparse
import time

import serial
from serial.tools import list_ports

from serial_car import DEFAULT_BAUD, find_pico_port


PROBE_COMMANDS = (
    "INFO",
    "PING",
    "S",
    "F 20 100",
    "S",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose the Pico USB serial bridge.")
    parser.add_argument("--port", help="Serial port, for example /dev/ttyACM0.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument(
        "--command",
        action="append",
        dest="commands",
        help="Extra command to send after the standard probe commands.",
    )
    return parser.parse_args()


def print_ports() -> None:
    print("Serial ports:")
    ports = list(list_ports.comports())
    if not ports:
        print("  none")
        return

    for port in ports:
        vid_pid = ""
        if port.vid is not None and port.pid is not None:
            vid_pid = f" vid:pid={port.vid:04x}:{port.pid:04x}"
        print(f"  {port.device} - {port.description}{vid_pid}")


def read_lines(device: serial.Serial, idle_seconds: float = 0.25) -> list[str]:
    lines: list[str] = []
    deadline = time.monotonic() + idle_seconds
    while time.monotonic() < deadline:
        if device.in_waiting == 0:
            time.sleep(0.02)
            continue
        line = device.readline().decode("utf-8", errors="replace").strip()
        if line:
            lines.append(line)
            deadline = time.monotonic() + idle_seconds
    return lines


def send_probe(device: serial.Serial, command: str) -> list[str]:
    device.write(command.encode("ascii") + b"\n")
    device.flush()
    return read_lines(device)


def classify(lines_by_command: dict[str, list[str]]) -> str:
    all_lines = [line for lines in lines_by_command.values() for line in lines]
    if "PONG" in all_lines:
        info_lines = [line for line in all_lines if line.startswith("INFO ")]
        if not info_lines:
            return (
                "Partial: bridge responds to PING, but does not report firmware info. "
                "Upload the latest bridge before movement tests."
            )
        if "motor_direction=-1" not in info_lines[-1]:
            return (
                "Partial: bridge responds, but motor polarity is not the corrected "
                "Freenove value motor_direction=-1."
            )
        return "OK: expected bridge firmware and corrected motor polarity are responding."
    if any("Pico confirma" in line or "recibi" in line for line in all_lines):
        return (
            "Mismatch: USB serial works, but the Pico is running a different "
            "echo/MicroPython-style program. Upload the MicroPython bridge next."
        )
    if not all_lines:
        return (
            "No response: serial port opens, but the firmware did not reply. "
            "Check the flashed sketch and baud rate."
        )
    return (
        "Unknown firmware response: USB serial works, but replies do not match "
        "micropython_serial_bridge."
    )


def main() -> int:
    args = parse_args()
    print_ports()
    port = find_pico_port(args.port)
    commands = list(PROBE_COMMANDS)
    if args.commands:
        commands.extend(args.commands)

    print(f"\nOpening {port} at {args.baud} baud")
    with serial.Serial(port, args.baud, timeout=0.2, write_timeout=0.2) as device:
        time.sleep(1.8)
        startup_lines = read_lines(device)
        if startup_lines:
            print("\nStartup lines:")
            for line in startup_lines:
                print(f"  {line}")

        lines_by_command: dict[str, list[str]] = {}
        for command in commands:
            print(f"\n> {command}")
            replies = send_probe(device, command)
            lines_by_command[command] = replies
            if replies:
                for reply in replies:
                    print(f"  {reply}")
            else:
                print("  no reply")
            time.sleep(0.1)

    print(f"\nResult: {classify(lines_by_command)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
