from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


PROTOCOL_VERSION = 1
MOTION_COMMAND_TYPE = "motion.command"
MOTION_SEQUENCE_TYPE = "motion.sequence"
MOTION_ACK_TYPE = "motion.ack"
MOTION_ERROR_TYPE = "motion.error"

ACTION_STOP = "stop"
ACTION_FORWARD = "forward"
ACTION_BACKWARD = "backward"
ACTION_LEFT = "left"
ACTION_RIGHT = "right"

ACTIONS = {
    ACTION_STOP,
    ACTION_FORWARD,
    ACTION_BACKWARD,
    ACTION_LEFT,
    ACTION_RIGHT,
}
MOVE_ACTIONS = ACTIONS - {ACTION_STOP}
WHEEL_MODES = {"ordinary", "mecanum"}

MIN_SPEED = 0
MAX_SPEED = 100
MIN_MOVE_DURATION_MS = 1
MAX_DURATION_MS = 5000


class MotionProtocolError(ValueError):
    pass


def normalize_action(action: str) -> str:
    aliases = {
        "f": ACTION_FORWARD,
        "w": ACTION_FORWARD,
        "b": ACTION_BACKWARD,
        "back": ACTION_BACKWARD,
        "s": ACTION_STOP,
        "l": ACTION_LEFT,
        "a": ACTION_LEFT,
        "r": ACTION_RIGHT,
        "d": ACTION_RIGHT,
    }
    action_key = str(action).strip().lower()
    return aliases.get(action_key, action_key)


def require_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise MotionProtocolError(f"{field_name} must be an integer.")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise MotionProtocolError(f"{field_name} must be an integer.") from exc


@dataclass(frozen=True)
class MotionCommand:
    action: str
    speed: int
    duration_ms: int
    wheel_mode: str = "ordinary"
    command_id: str = ""
    source: str = "local"
    version: int = PROTOCOL_VERSION
    command_type: str = MOTION_COMMAND_TYPE

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MotionCommand":
        command = cls(
            version=require_int(payload.get("version", PROTOCOL_VERSION), "version"),
            command_type=str(payload.get("type", MOTION_COMMAND_TYPE)),
            command_id=str(payload.get("id", payload.get("command_id", ""))),
            source=str(payload.get("source", "local")),
            action=str(payload.get("action", "")),
            speed=require_int(payload.get("speed", 0), "speed"),
            duration_ms=require_int(payload.get("duration_ms", 0), "duration_ms"),
            wheel_mode=str(payload.get("wheel_mode", "ordinary")),
        )
        return command.normalized()

    def normalized(self) -> "MotionCommand":
        action = normalize_action(self.action)
        speed = require_int(self.speed, "speed")
        duration_ms = require_int(self.duration_ms, "duration_ms")
        wheel_mode = str(self.wheel_mode).strip().lower()

        if action == ACTION_STOP:
            speed = 0
            duration_ms = 0

        command = MotionCommand(
            version=self.version,
            command_type=self.command_type,
            command_id=self.command_id,
            source=self.source,
            action=action,
            speed=speed,
            duration_ms=duration_ms,
            wheel_mode=wheel_mode,
        )
        command.validate()
        return command

    def validate(self) -> None:
        if self.version != PROTOCOL_VERSION:
            raise MotionProtocolError(f"Unsupported protocol version: {self.version}")
        if self.command_type != MOTION_COMMAND_TYPE:
            raise MotionProtocolError(f"Unsupported command type: {self.command_type}")
        if self.action not in ACTIONS:
            raise MotionProtocolError(f"Unsupported action: {self.action}")
        if self.wheel_mode not in WHEEL_MODES:
            raise MotionProtocolError(f"Unsupported wheel_mode: {self.wheel_mode}")
        if not MIN_SPEED <= self.speed <= MAX_SPEED:
            raise MotionProtocolError(f"speed must be between {MIN_SPEED} and {MAX_SPEED}.")
        if self.action in MOVE_ACTIONS and self.speed == 0:
            raise MotionProtocolError("Movement commands require speed greater than 0.")
        if self.action in MOVE_ACTIONS:
            if not MIN_MOVE_DURATION_MS <= self.duration_ms <= MAX_DURATION_MS:
                raise MotionProtocolError(
                    f"duration_ms must be between {MIN_MOVE_DURATION_MS} and "
                    f"{MAX_DURATION_MS} for movement commands."
                )
        if self.action == ACTION_STOP and (self.speed != 0 or self.duration_ms != 0):
            raise MotionProtocolError("stop commands must use speed=0 and duration_ms=0.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "type": self.command_type,
            "id": self.command_id,
            "source": self.source,
            "action": self.action,
            "speed": self.speed,
            "duration_ms": self.duration_ms,
            "wheel_mode": self.wheel_mode,
        }


@dataclass(frozen=True)
class MotionSequence:
    sequence_id: str
    name: str
    steps: list[MotionCommand] = field(default_factory=list)
    version: int = PROTOCOL_VERSION
    sequence_type: str = MOTION_SEQUENCE_TYPE

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MotionSequence":
        version = require_int(payload.get("version", PROTOCOL_VERSION), "version")
        sequence_type = str(payload.get("type", MOTION_SEQUENCE_TYPE))
        sequence_id = str(payload.get("id", payload.get("sequence_id", "")))
        name = str(payload.get("name", sequence_id or "motion-sequence"))
        default_speed = require_int(payload.get("default_speed", 20), "default_speed")
        default_wheel_mode = str(payload.get("wheel_mode", "ordinary"))
        raw_steps = payload.get("steps", [])

        if version != PROTOCOL_VERSION:
            raise MotionProtocolError(f"Unsupported sequence version: {version}")
        if sequence_type != MOTION_SEQUENCE_TYPE:
            raise MotionProtocolError(f"Unsupported sequence type: {sequence_type}")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise MotionProtocolError("Motion sequences require a non-empty steps list.")

        commands: list[MotionCommand] = []
        for index, raw_step in enumerate(raw_steps, start=1):
            if not isinstance(raw_step, dict):
                raise MotionProtocolError(f"Step {index} must be an object.")
            step = dict(raw_step)
            step.setdefault("version", PROTOCOL_VERSION)
            step.setdefault("type", MOTION_COMMAND_TYPE)
            step.setdefault("id", f"{sequence_id}:{index}")
            step.setdefault("source", f"sequence:{sequence_id}")
            step.setdefault("speed", 0 if normalize_action(step.get("action", "")) == ACTION_STOP else default_speed)
            step.setdefault("duration_ms", 0)
            step.setdefault("wheel_mode", default_wheel_mode)
            commands.append(MotionCommand.from_dict(step))

        return cls(
            version=version,
            sequence_type=sequence_type,
            sequence_id=sequence_id,
            name=name,
            steps=commands,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "type": self.sequence_type,
            "id": self.sequence_id,
            "name": self.name,
            "steps": [step.to_dict() for step in self.steps],
        }


def ack(command: MotionCommand, status: str = "accepted") -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": MOTION_ACK_TYPE,
        "id": command.command_id,
        "status": status,
    }


def error(command_id: str, code: str, message: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "type": MOTION_ERROR_TYPE,
        "id": command_id,
        "code": code,
        "message": message,
    }
