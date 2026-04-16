from __future__ import annotations


ORDINARY_TURN_SPEED_SCALE = 0.65


class PicoCommandError(ValueError):
    pass


def build_pico_motion_line(action: str, speed: int, duration_ms: int, wheel_mode: str) -> str:
    action_key = action.strip().lower()
    mode = wheel_mode.strip().lower()

    if action_key == "stop":
        return "S"
    if mode not in {"ordinary", "mecanum"}:
        raise PicoCommandError(f"Unsupported wheel mode: {wheel_mode}")
    if not 0 <= speed <= 100:
        raise PicoCommandError("Speed must be between 0 and 100.")
    if duration_ms < 0:
        raise PicoCommandError("duration_ms must not be negative.")

    if action_key == "forward":
        return f"F {speed} {duration_ms}"
    if action_key == "backward":
        return f"B {speed} {duration_ms}"

    if mode == "mecanum":
        if action_key == "left":
            return f"ML {speed} {duration_ms}"
        if action_key == "right":
            return f"MR {speed} {duration_ms}"
    else:
        turn_speed = scaled_turn_speed(speed)
        if action_key == "left":
            return f"DRIVE 0 {turn_speed} {duration_ms}"
        if action_key == "right":
            return f"DRIVE {turn_speed} 0 {duration_ms}"

    raise PicoCommandError(f"Unsupported action: {action}")


def scaled_turn_speed(speed: int) -> int:
    if speed <= 0:
        return 0
    return max(1, min(100, round(speed * ORDINARY_TURN_SPEED_SCALE)))
