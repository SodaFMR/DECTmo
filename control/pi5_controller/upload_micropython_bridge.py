from __future__ import annotations

import argparse
import time
from pathlib import Path

import serial

from serial_car import DEFAULT_BAUD, find_pico_port


CTRL_A = b"\x01"
CTRL_B = b"\x02"
CTRL_C = b"\x03"
CTRL_D = b"\x04"


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    default_source = root / "pico_micropython_bridge" / "main.py"

    parser = argparse.ArgumentParser(
        description="Upload the MicroPython motor bridge as main.py on the Pico."
    )
    parser.add_argument("--port", help="Serial port, for example /dev/ttyACM0.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument(
        "--source",
        type=Path,
        default=default_source,
        help="Bridge source file to write to the Pico as main.py.",
    )
    return parser.parse_args()


def read_until(device: serial.Serial, marker: bytes, timeout: float) -> bytes:
    data = b""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        chunk = device.read(device.in_waiting or 1)
        if chunk:
            data += chunk
            if marker in data:
                return data
        else:
            time.sleep(0.02)
    raise TimeoutError(f"Timed out waiting for {marker!r}. Received: {data!r}")


def enter_raw_repl(device: serial.Serial) -> None:
    device.write(CTRL_C)
    device.write(CTRL_C)
    device.flush()
    time.sleep(0.4)
    device.reset_input_buffer()

    device.write(CTRL_A)
    device.flush()
    response = read_until(device, b">", 3.0)
    if b"raw REPL" not in response:
        raise RuntimeError(response.decode("utf-8", errors="replace"))


def raw_exec(device: serial.Serial, code: str, timeout: float = 5.0) -> bytes:
    device.write(code.encode("utf-8"))
    device.write(CTRL_D)
    device.flush()

    response = read_until(device, b"\x04>", timeout)
    if b"OK" not in response:
        raise RuntimeError(response.decode("utf-8", errors="replace"))
    if b"Traceback" in response:
        raise RuntimeError(response.decode("utf-8", errors="replace"))
    return response


def upload_file(device: serial.Serial, content: bytes) -> None:
    raw_exec(device, "f = open('main.py', 'wb')\nf.close()\n")
    chunk_size = 512
    for offset in range(0, len(content), chunk_size):
        chunk = content[offset : offset + chunk_size]
        raw_exec(device, "with open('main.py', 'ab') as f:\n    f.write({!r})\n".format(chunk))
        print(f"Uploaded {min(offset + chunk_size, len(content))}/{len(content)} bytes")


def main() -> int:
    args = parse_args()
    source = args.source.resolve()
    if not source.exists():
        raise SystemExit(f"Bridge source not found: {source}")

    port = find_pico_port(args.port)
    content = source.read_bytes()
    print(f"Opening {port} at {args.baud} baud")
    print(f"Uploading {source} to Pico:/main.py")

    with serial.Serial(port, args.baud, timeout=0.2, write_timeout=1.0) as device:
        time.sleep(1.0)
        enter_raw_repl(device)
        upload_file(device, content)
        print("Resetting Pico")
        try:
            raw_exec(device, "import machine\nmachine.reset()\n", timeout=2.0)
        except (TimeoutError, serial.SerialException):
            pass
        finally:
            try:
                device.write(CTRL_B)
                device.flush()
            except serial.SerialException:
                pass

    print("Upload complete. Wait two seconds, then start web_control.py or run a dry-run movement.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
