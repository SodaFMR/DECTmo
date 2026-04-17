from __future__ import annotations

import argparse

from serial.tools import list_ports

from nrf_modem import (
    DEFAULT_AT_TIMEOUT,
    DEFAULT_NRF_BAUD,
    NrfModemProbe,
    candidate_nrf_ports,
    probe_nrf_modem_port,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find the nRF9151 USB VCOM port that responds to safe AT commands."
    )
    parser.add_argument(
        "--port",
        action="append",
        dest="ports",
        help="Serial port to probe. May be passed more than once.",
    )
    parser.add_argument("--baud", type=int, default=DEFAULT_NRF_BAUD)
    parser.add_argument("--timeout", type=float, default=DEFAULT_AT_TIMEOUT)
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


def print_result(result: NrfModemProbe) -> None:
    print(f"\n=== {result.port} ===")
    for command_result in (result.at, result.firmware):
        print(f"> {command_result.command}")
        if command_result.lines:
            for line in command_result.lines:
                print(line)
        else:
            print("no reply")

    if result.is_modem_port:
        print(f"Result: OK modem AT port, firmware={result.firmware_version}")
    elif result.responds_to_at:
        print("Result: Partial AT port, but firmware version was not reported.")
    else:
        print("Result: No AT response on this port.")


def main() -> int:
    args = parse_args()
    print_ports()
    ports = args.ports or candidate_nrf_ports()
    if not ports:
        print("\nNo SEGGER J-Link/nRF candidate serial ports found.")
        return 1

    print("\nSafe probe commands: AT, AT+CGMR")
    found_modem = False
    for port in ports:
        try:
            result = probe_nrf_modem_port(port, args.baud, args.timeout)
        except Exception as exc:
            print(f"\n=== {port} ===")
            print(f"error: {exc}")
            continue
        print_result(result)
        found_modem = found_modem or result.is_modem_port

    if found_modem:
        print(
            "\nSummary: USB modem connectivity is working. This does not prove "
            "DECT NR+ packet transport yet."
        )
        return 0

    print("\nSummary: No nRF modem AT port was found.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
