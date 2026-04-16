from __future__ import annotations

import argparse
import json
from pathlib import Path

from motion_controller import MotionController
from motion_protocol import MotionCommand, MotionProtocolError, MotionSequence


SEQUENCE_DIR = Path(__file__).resolve().parent / "sequences"
DEFAULT_BAUD = 115200


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run validated motion command sequences.")
    parser.add_argument("sequence", nargs="?", help="Sequence JSON path or built-in sequence name.")
    parser.add_argument("--list", action="store_true", help="List built-in sequences.")
    parser.add_argument("--execute", action="store_true", help="Move the physical car.")
    parser.add_argument("--port", help="Serial port, for example /dev/ttyACM0.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--gap-ms", type=int, default=150)
    parser.add_argument("--speed", type=int, help="Override speed for all movement steps.")
    parser.add_argument(
        "--wheel-mode",
        choices=("ordinary", "mecanum"),
        help="Override wheel mode for all steps.",
    )
    return parser.parse_args()


def list_sequences() -> None:
    print("Built-in sequences:")
    for path in sorted(SEQUENCE_DIR.glob("*.json")):
        print(f"  {path.stem}")


def resolve_sequence_path(sequence: str) -> Path:
    candidate = Path(sequence)
    if candidate.exists():
        return candidate

    builtin = SEQUENCE_DIR / f"{sequence}.json"
    if builtin.exists():
        return builtin

    raise FileNotFoundError(f"Sequence not found: {sequence}")


def load_sequence(path: Path) -> MotionSequence:
    return MotionSequence.from_dict(json.loads(path.read_text(encoding="utf-8")))


def apply_overrides(
    sequence: MotionSequence,
    speed: int | None,
    wheel_mode: str | None,
) -> MotionSequence:
    if speed is None and wheel_mode is None:
        return sequence

    steps: list[MotionCommand] = []
    for step in sequence.steps:
        payload = step.to_dict()
        if speed is not None and step.action != "stop":
            payload["speed"] = speed
        if wheel_mode is not None:
            payload["wheel_mode"] = wheel_mode
        steps.append(MotionCommand.from_dict(payload))

    return MotionSequence(
        version=sequence.version,
        sequence_type=sequence.sequence_type,
        sequence_id=sequence.sequence_id,
        name=sequence.name,
        steps=steps,
    )


def print_result(result: dict[str, object]) -> None:
    print(json.dumps(result, sort_keys=True))


def main() -> int:
    args = parse_args()
    if args.list:
        list_sequences()
        return 0
    if not args.sequence:
        raise SystemExit("Provide a sequence name/path or use --list.")

    try:
        sequence = apply_overrides(
            load_sequence(resolve_sequence_path(args.sequence)),
            args.speed,
            args.wheel_mode,
        )
    except (FileNotFoundError, json.JSONDecodeError, MotionProtocolError) as exc:
        print(f"Sequence error: {exc}")
        return 1

    dry_run = not args.execute
    print(f"Sequence: {sequence.sequence_id} ({sequence.name})")
    print(f"Mode: {'execute' if args.execute else 'dry-run'}")

    try:
        if dry_run:
            controller = MotionController(dry_run=True)
            results = controller.execute_sequence(sequence.steps, gap_ms=args.gap_ms)
        else:
            from serial_car import SerialCar

            with SerialCar(args.port, args.baud) as car:
                controller = MotionController(car=car, dry_run=False)
                results = controller.execute_sequence(sequence.steps, gap_ms=args.gap_ms)
        for result in results:
            print_result(result.to_dict())
    except (RuntimeError, MotionProtocolError) as exc:
        print(f"Execution error: {exc}")
        return 1
    except Exception as exc:
        if exc.__class__.__name__ == "SerialCarError":
            print(f"Execution error: {exc}")
            return 1
        raise

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
