from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "control" / "pi5_controller"))

from motion_protocol import MotionCommand, MotionProtocolError, MotionSequence
from web_motion import web_command_payload


class MotionProtocolTest(unittest.TestCase):
    def test_valid_command_normalizes_alias(self) -> None:
        command = MotionCommand.from_dict(
            {
                "action": "w",
                "speed": 25,
                "duration_ms": 300,
            }
        )
        self.assertEqual(command.action, "forward")
        self.assertEqual(command.speed, 25)

    def test_stop_normalizes_speed_and_duration(self) -> None:
        command = MotionCommand.from_dict(
            {
                "action": "stop",
                "speed": 99,
                "duration_ms": 4000,
            }
        )
        self.assertEqual(command.speed, 0)
        self.assertEqual(command.duration_ms, 0)

    def test_movement_requires_nonzero_speed(self) -> None:
        with self.assertRaises(MotionProtocolError):
            MotionCommand.from_dict(
                {
                    "action": "forward",
                    "speed": 0,
                    "duration_ms": 300,
                }
            )

    def test_sequence_loads_default_speed(self) -> None:
        sequence = MotionSequence.from_dict(
            {
                "version": 1,
                "type": "motion.sequence",
                "id": "test",
                "default_speed": 20,
                "steps": [
                    {"action": "forward", "duration_ms": 100},
                    {"action": "stop"},
                ],
            }
        )
        self.assertEqual(sequence.steps[0].speed, 20)
        self.assertEqual(sequence.steps[1].speed, 0)

    def test_builtin_sequences_validate(self) -> None:
        sequence_dir = ROOT / "control" / "pi5_controller" / "sequences"
        for path in sequence_dir.glob("*.json"):
            with self.subTest(path=path.name):
                MotionSequence.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def test_web_payload_becomes_motion_command(self) -> None:
        payload = web_command_payload(
            {
                "action": "forward",
                "speed": 33,
                "wheelMode": "ordinary",
            },
            default_wheel_mode="ordinary",
            default_duration_ms=250,
        )
        command = MotionCommand.from_dict(payload)
        self.assertEqual(command.action, "forward")
        self.assertEqual(command.speed, 33)
        self.assertEqual(command.duration_ms, 250)
        self.assertEqual(command.source, "web")


if __name__ == "__main__":
    unittest.main()
