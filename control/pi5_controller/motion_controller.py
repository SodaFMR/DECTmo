from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from motion_protocol import MotionCommand, ack


class CarTransport(Protocol):
    def send_move(self, action: str, speed: int, duration_ms: int, wheel_mode: str) -> None:
        ...

    def stop(self) -> None:
        ...


@dataclass(frozen=True)
class MotionResult:
    command: MotionCommand
    dry_run: bool
    status: str

    def to_dict(self) -> dict[str, object]:
        body = ack(self.command, self.status)
        body["dry_run"] = self.dry_run
        body["command"] = self.command.to_dict()
        return body


class MotionController:
    def __init__(self, car: CarTransport | None = None, dry_run: bool = True) -> None:
        self.car = car
        self.dry_run = dry_run

    def execute(self, command: MotionCommand, wait: bool = False) -> MotionResult:
        command = command.normalized()

        if not self.dry_run:
            if self.car is None:
                raise RuntimeError("A car transport is required when dry_run is false.")
            if command.action == "stop":
                self.car.stop()
            else:
                self.car.send_move(
                    command.action,
                    command.speed,
                    command.duration_ms,
                    command.wheel_mode,
                )

        if wait and command.duration_ms > 0:
            time.sleep(command.duration_ms / 1000)

        return MotionResult(command=command, dry_run=self.dry_run, status="accepted")

    def execute_sequence(
        self,
        commands: list[MotionCommand],
        gap_ms: int = 150,
    ) -> list[MotionResult]:
        results: list[MotionResult] = []
        for command in commands:
            results.append(self.execute(command, wait=True))
            if gap_ms > 0:
                time.sleep(gap_ms / 1000)
        return results
