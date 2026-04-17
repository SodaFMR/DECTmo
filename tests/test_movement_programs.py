from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "control" / "pi5_controller"))

from movement_programs import (
    MOVEMENT_DIR,
    MovementRecorder,
    list_json_movements,
    list_programs,
    load_movements,
    movements_from_program,
    program_movement_test_1,
    program_movement_test_2,
)


class MovementProgramsTest(unittest.TestCase):
    def test_program_movement_test_1_is_predictable(self) -> None:
        recorder = MovementRecorder()

        program_movement_test_1(recorder, speed=20, duration_ms=250)

        self.assertEqual(
            [movement.action for movement in recorder.movements],
            ["left", "right", "forward", "backward"],
        )

    def test_program_movement_test_2_repeats_forward_then_backward(self) -> None:
        movements = movements_from_program("test_2", speed=20, duration_ms=250)

        self.assertEqual(
            [movement.action for movement in movements],
            ["forward", "forward", "forward", "forward", "backward", "backward", "backward", "backward"],
        )

    def test_builtin_json_movements_load(self) -> None:
        for path in MOVEMENT_DIR.glob("*.json"):
            with self.subTest(path=path.name):
                movements = load_movements(path)
                self.assertTrue(movements)

    def test_lists_available_programs_and_json_files(self) -> None:
        self.assertIn("test_1", list_programs())
        self.assertIn("direction_check", list_json_movements())


if __name__ == "__main__":
    unittest.main()
