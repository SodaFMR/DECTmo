from __future__ import annotations

import argparse
import curses
import time

from serial_car import DEFAULT_BAUD, DEFAULT_PULSE_MS, SerialCar, SerialCarError


KEY_ACTIONS = {
    ord("w"): "forward",
    ord("W"): "forward",
    curses.KEY_UP: "forward",
    ord("s"): "backward",
    ord("S"): "backward",
    curses.KEY_DOWN: "backward",
    ord("a"): "left",
    ord("A"): "left",
    curses.KEY_LEFT: "left",
    ord("d"): "right",
    ord("D"): "right",
    curses.KEY_RIGHT: "right",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keyboard controller for the Pico car.")
    parser.add_argument("--port", help="Serial port, for example /dev/ttyACM0.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--speed", type=int, default=50)
    parser.add_argument("--pulse-ms", type=int, default=DEFAULT_PULSE_MS)
    parser.add_argument(
        "--wheel-mode",
        choices=("ordinary", "mecanum"),
        default="ordinary",
        help="In ordinary mode left/right turn. In mecanum mode left/right strafe.",
    )
    return parser.parse_args()


def clamp_speed(speed: int) -> int:
    return max(0, min(100, speed))


def draw_status(screen, car: SerialCar, speed: int, wheel_mode: str, last_action: str) -> None:
    screen.erase()
    screen.addstr(0, 0, "Freenove 4WD USB controller")
    screen.addstr(2, 0, f"Serial: {car.port} @ {car.baud}")
    screen.addstr(3, 0, f"Mode: {wheel_mode}")
    screen.addstr(4, 0, f"Speed: {speed}")
    screen.addstr(5, 0, f"Last action: {last_action}")
    screen.addstr(7, 0, "W/Up: forward   S/Down: backward")
    screen.addstr(8, 0, "A/Left: left     D/Right: right")
    screen.addstr(9, 0, "Space: stop      +/-: speed      Q: quit")
    screen.addstr(11, 0, "Hold a movement key or tap repeatedly. The Pico failsafe stops the motors.")
    screen.refresh()


def run_curses(screen, args: argparse.Namespace) -> None:
    curses.curs_set(0)
    screen.nodelay(True)
    screen.timeout(50)

    speed = clamp_speed(args.speed)
    last_action = "stop"

    with SerialCar(args.port, args.baud) as car:
        draw_status(screen, car, speed, args.wheel_mode, last_action)
        while True:
            key = screen.getch()
            if key == -1:
                time.sleep(0.02)
                continue
            if key in (ord("q"), ord("Q")):
                car.stop()
                break
            if key in (ord("+"), ord("=")):
                speed = clamp_speed(speed + 5)
                draw_status(screen, car, speed, args.wheel_mode, last_action)
                continue
            if key in (ord("-"), ord("_")):
                speed = clamp_speed(speed - 5)
                draw_status(screen, car, speed, args.wheel_mode, last_action)
                continue
            if key == ord(" "):
                car.stop()
                last_action = "stop"
                draw_status(screen, car, speed, args.wheel_mode, last_action)
                continue
            action = KEY_ACTIONS.get(key)
            if action is None:
                continue
            car.send_move(action, speed, args.pulse_ms, args.wheel_mode)
            last_action = action
            draw_status(screen, car, speed, args.wheel_mode, last_action)


def main() -> int:
    args = parse_args()
    try:
        curses.wrapper(run_curses, args)
    except SerialCarError as exc:
        print(f"Serial controller error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
