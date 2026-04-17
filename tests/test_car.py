from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "control" / "pi5_controller"))

from car import CarError, Movement, build_pico_line, normalize_action


class CarTest(unittest.TestCase):
    def test_action_aliases_are_normalized(self) -> None:
        self.assertEqual(normalize_action("w"), "forward")
        self.assertEqual(normalize_action("backwards"), "backward")
        self.assertEqual(normalize_action("A"), "left")

    def test_movement_from_dict_uses_defaults(self) -> None:
        movement = Movement.from_dict({"action": "forward"}, default_speed=20, default_duration_ms=250)

        self.assertEqual(movement.action, "forward")
        self.assertEqual(movement.speed, 20)
        self.assertEqual(movement.duration_ms, 250)

    def test_stop_normalizes_speed_but_keeps_duration_for_pause(self) -> None:
        movement = Movement.from_dict({"action": "stop", "speed": 50, "duration_ms": 100})

        self.assertEqual(movement.action, "stop")
        self.assertEqual(movement.speed, 0)
        self.assertEqual(movement.duration_ms, 100)

    def test_movement_requires_nonzero_speed(self) -> None:
        with self.assertRaises(CarError):
            Movement(action="forward", speed=0, duration_ms=250).normalized()

    def test_forward_builds_pico_line(self) -> None:
        movement = Movement(action="forward", speed=50, duration_ms=250)

        self.assertEqual(build_pico_line(movement), "F 50 250")

    def test_ordinary_left_uses_gentle_pivot(self) -> None:
        movement = Movement(action="left", speed=50, duration_ms=250)

        self.assertEqual(build_pico_line(movement), "DRIVE 0 32 250")

    def test_ordinary_right_uses_gentle_pivot(self) -> None:
        movement = Movement(action="right", speed=50, duration_ms=250)

        self.assertEqual(build_pico_line(movement), "DRIVE 32 0 250")

    def test_mecanum_left_strafes(self) -> None:
        movement = Movement(action="left", speed=50, duration_ms=250)

        self.assertEqual(build_pico_line(movement, wheel_mode="mecanum"), "ML 50 250")


if __name__ == "__main__":
    unittest.main()
