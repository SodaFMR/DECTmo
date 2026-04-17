from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "control" / "pi5_controller"))

from dect_packet import (
    DectAckPacket,
    DectCommandPacket,
    DectErrorPacket,
    DectHeartbeatPacket,
    DectPacketError,
    decode_motion_command,
    decode_packet,
    encode_ack,
    encode_error,
    encode_heartbeat,
    encode_motion_command,
)
from motion_protocol import MotionCommand


class DectPacketTest(unittest.TestCase):
    def test_motion_command_round_trips_as_binary_packet(self) -> None:
        command = MotionCommand.from_dict(
            {
                "action": "forward",
                "speed": 35,
                "duration_ms": 300,
                "wheel_mode": "ordinary",
            }
        )

        packet = decode_packet(encode_motion_command(command, sequence_id=42))

        self.assertIsInstance(packet, DectCommandPacket)
        assert isinstance(packet, DectCommandPacket)
        self.assertEqual(packet.sequence_id, 42)
        self.assertEqual(packet.command.command_id, "42")
        self.assertEqual(packet.command.source, "remote-dect")
        self.assertEqual(packet.command.action, "forward")
        self.assertEqual(packet.command.speed, 35)
        self.assertEqual(packet.command.duration_ms, 300)
        self.assertEqual(packet.command.wheel_mode, "ordinary")

    def test_emergency_stop_round_trips_with_stop_normalization(self) -> None:
        command = MotionCommand.from_dict(
            {
                "action": "stop",
                "speed": 99,
                "duration_ms": 4000,
            }
        )

        packet = decode_packet(
            encode_motion_command(command, sequence_id=7, emergency_stop=True)
        )

        self.assertIsInstance(packet, DectCommandPacket)
        assert isinstance(packet, DectCommandPacket)
        self.assertTrue(packet.emergency_stop)
        self.assertEqual(packet.command.action, "stop")
        self.assertEqual(packet.command.speed, 0)
        self.assertEqual(packet.command.duration_ms, 0)

    def test_emergency_flag_requires_stop_action(self) -> None:
        command = MotionCommand.from_dict(
            {
                "action": "forward",
                "speed": 20,
                "duration_ms": 200,
            }
        )

        with self.assertRaises(DectPacketError):
            encode_motion_command(command, sequence_id=1, emergency_stop=True)

    def test_ack_packet_round_trips(self) -> None:
        packet = decode_packet(encode_ack(sequence_id=101, status="executed"))

        self.assertIsInstance(packet, DectAckPacket)
        assert isinstance(packet, DectAckPacket)
        self.assertEqual(packet.sequence_id, 101)
        self.assertEqual(packet.status, "executed")

    def test_error_packet_round_trips(self) -> None:
        packet = decode_packet(
            encode_error(
                sequence_id=102,
                code="invalid_command",
                message="speed must be greater than zero",
            )
        )

        self.assertIsInstance(packet, DectErrorPacket)
        assert isinstance(packet, DectErrorPacket)
        self.assertEqual(packet.sequence_id, 102)
        self.assertEqual(packet.code, "invalid_command")
        self.assertEqual(packet.message, "speed must be greater than zero")

    def test_heartbeat_packet_round_trips(self) -> None:
        packet = decode_packet(encode_heartbeat(sequence_id=500))

        self.assertIsInstance(packet, DectHeartbeatPacket)
        assert isinstance(packet, DectHeartbeatPacket)
        self.assertEqual(packet.sequence_id, 500)

    def test_crc_mismatch_is_rejected(self) -> None:
        command = MotionCommand.from_dict(
            {
                "action": "right",
                "speed": 25,
                "duration_ms": 150,
            }
        )
        frame = bytearray(encode_motion_command(command, sequence_id=99))
        frame[-1] ^= 0x01

        with self.assertRaisesRegex(DectPacketError, "CRC"):
            decode_packet(bytes(frame))

    def test_decode_motion_command_rejects_non_command_packet(self) -> None:
        with self.assertRaises(DectPacketError):
            decode_motion_command(encode_ack(sequence_id=1))


if __name__ == "__main__":
    unittest.main()
