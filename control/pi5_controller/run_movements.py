from __future__ import annotations

import argparse
import json

from car import DEFAULT_BAUD, DEFAULT_DURATION_MS, DEFAULT_SPEED, Car, CarError
from movement_programs import (
    list_json_movements,
    list_programs,
    load_movements,
    movements_from_program,
    resolve_movement_file,
    run_movements,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run simple car movement programs.")
    parser.add_argument("name", nargs="?", help="Built-in program name or movement JSON file.")
    parser.add_argument("--list", action="store_true", help="List available programs and JSON files.")
    parser.add_argument("--execute", action="store_true", help="Move the physical car.")
    parser.add_argument("--port", help="Pico serial port, for example /dev/ttyACM0.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--speed", type=int, help="Override movement speed.")
    parser.add_argument("--duration-ms", type=int, help="Override movement duration.")
    parser.add_argument("--gap-ms", type=int, default=150)
    return parser.parse_args()


def print_available() -> None:
    print("Built-in programs:")
    for name in list_programs():
        print(f"  {name}")
    print("\nJSON movement files:")
    for name in list_json_movements():
        print(f"  {name}")


def load_by_name(name: str, speed: int | None, duration_ms: int | None):
    if name in list_programs():
        return movements_from_program(
            name,
            speed=DEFAULT_SPEED if speed is None else speed,
            duration_ms=DEFAULT_DURATION_MS if duration_ms is None else duration_ms,
        )
    return load_movements(resolve_movement_file(name), speed=speed, duration_ms=duration_ms)


def main() -> int:
    args = parse_args()
    if args.list:
        print_available()
        return 0
    if not args.name:
        raise SystemExit("Provide a program/JSON name or use --list.")

    try:
        movements = load_by_name(args.name, speed=args.speed, duration_ms=args.duration_ms)
    except (FileNotFoundError, ValueError, json.JSONDecodeError, CarError) as exc:
        print(f"Movement error: {exc}")
        return 1

    print(f"Movement plan: {args.name}")
    print(f"Mode: {'execute' if args.execute else 'dry-run'}")
    for movement in movements:
        print(json.dumps(movement.to_dict(), sort_keys=True))

    if not args.execute:
        return 0

    try:
        with Car(args.port, args.baud) as car:
            run_movements(car, movements, gap_ms=args.gap_ms)
    except CarError as exc:
        print(f"Car error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
