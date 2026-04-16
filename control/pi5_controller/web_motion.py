from __future__ import annotations

import time

from motion_protocol import PROTOCOL_VERSION


def web_command_payload(
    payload: dict[str, object],
    default_wheel_mode: str,
    default_duration_ms: int,
) -> dict[str, object]:
    action = str(payload.get("action", "stop"))
    wheel_mode = str(payload.get("wheel_mode", payload.get("wheelMode", default_wheel_mode)))
    duration_ms = int(payload.get("duration_ms", payload.get("durationMs", default_duration_ms)))
    speed = int(payload.get("speed", 0 if action == "stop" else 50))
    if action == "stop":
        speed = 0
        duration_ms = 0

    return {
        "version": int(payload.get("version", PROTOCOL_VERSION)),
        "type": str(payload.get("type", "motion.command")),
        "id": str(payload.get("id", f"web-{time.monotonic_ns()}")),
        "source": str(payload.get("source", "web")),
        "action": action,
        "speed": speed,
        "duration_ms": duration_ms,
        "wheel_mode": wheel_mode,
    }
