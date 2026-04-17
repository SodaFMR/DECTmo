from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Protocol

from car import DEFAULT_DURATION_MS, DEFAULT_SPEED, Movement


MOVEMENT_DIR = Path(__file__).resolve().parent / "movements"


class MovementCar(Protocol):
    def send_move(
        self,
        action: str,
        duration_ms: int = DEFAULT_DURATION_MS,
        speed: int = DEFAULT_SPEED,
    ) -> Movement:
        ...


class MovementRecorder:
    def __init__(self) -> None:
        self.movements: list[Movement] = []

    def send_move(
        self,
        action: str,
        duration_ms: int = DEFAULT_DURATION_MS,
        speed: int = DEFAULT_SPEED,
    ) -> Movement:
        movement = Movement(action=action, duration_ms=duration_ms, speed=speed).normalized()
        self.movements.append(movement)
        return movement


Program = Callable[[MovementCar, int, int], None]


def program_movement_test_1(
    car: MovementCar,
    speed: int = DEFAULT_SPEED,
    duration_ms: int = DEFAULT_DURATION_MS,
) -> None:
    car.send_move(action="left", duration_ms=duration_ms, speed=speed)
    car.send_move(action="right", duration_ms=duration_ms, speed=speed)
    car.send_move(action="forward", duration_ms=duration_ms, speed=speed)
    car.send_move(action="backward", duration_ms=duration_ms, speed=speed)


def program_movement_test_2(
    car: MovementCar,
    speed: int = DEFAULT_SPEED,
    duration_ms: int = DEFAULT_DURATION_MS,
) -> None:
    for _ in range(4):
        car.send_move(action="forward", duration_ms=duration_ms, speed=speed)
    for _ in range(4):
        car.send_move(action="backward", duration_ms=duration_ms, speed=speed)


PROGRAMS: dict[str, Program] = {
    "test_1": program_movement_test_1,
    "test_2": program_movement_test_2,
}


def list_programs() -> list[str]:
    return sorted(PROGRAMS)


def list_json_movements() -> list[str]:
    return sorted(path.stem for path in MOVEMENT_DIR.glob("*.json"))


def movements_from_program(
    name: str,
    speed: int = DEFAULT_SPEED,
    duration_ms: int = DEFAULT_DURATION_MS,
) -> list[Movement]:
    try:
        program = PROGRAMS[name]
    except KeyError as exc:
        raise ValueError(f"Unknown movement program: {name}") from exc

    recorder = MovementRecorder()
    program(recorder, speed, duration_ms)
    return recorder.movements


def resolve_movement_file(name_or_path: str) -> Path:
    path = Path(name_or_path)
    if path.exists():
        return path

    builtin = MOVEMENT_DIR / f"{name_or_path}.json"
    if builtin.exists():
        return builtin

    raise FileNotFoundError(f"Movement file not found: {name_or_path}")


def load_movements(
    json_file: str | Path,
    speed: int | None = None,
    duration_ms: int | None = None,
) -> list[Movement]:
    payload = json.loads(Path(json_file).read_text(encoding="utf-8"))
    default_speed = int(payload.get("default_speed", DEFAULT_SPEED if speed is None else speed))
    default_duration_ms = int(
        payload.get(
            "default_duration_ms",
            DEFAULT_DURATION_MS if duration_ms is None else duration_ms,
        )
    )
    raw_movements = payload.get("movements", payload.get("steps", []))
    if not isinstance(raw_movements, list) or not raw_movements:
        raise ValueError("Movement JSON must contain a non-empty movements list.")

    movements: list[Movement] = []
    for index, item in enumerate(raw_movements, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Movement {index} must be an object.")
        movement_payload = dict(item)
        if speed is not None and movement_payload.get("action") != "stop":
            movement_payload["speed"] = speed
        if duration_ms is not None and movement_payload.get("duration_ms") is None:
            movement_payload["duration_ms"] = duration_ms
        movements.append(
            Movement.from_dict(
                movement_payload,
                default_speed=default_speed,
                default_duration_ms=default_duration_ms,
            )
        )
    return movements


def run_movements(
    car: MovementCar,
    movements: list[Movement],
    gap_ms: int = 150,
) -> list[Movement]:
    executed: list[Movement] = []
    for movement in movements:
        executed.append(
            car.send_move(
                action=movement.action,
                duration_ms=movement.duration_ms,
                speed=movement.speed,
            )
        )
        sleep_ms = movement.duration_ms + gap_ms
        if sleep_ms > 0:
            time.sleep(sleep_ms / 1000)
    return executed
