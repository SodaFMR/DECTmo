from __future__ import annotations

import binascii
import struct
from dataclasses import dataclass
from typing import Union

from motion_protocol import MotionCommand, MotionProtocolError


PACKET_VERSION = 1
MAGIC = b"DM"

MESSAGE_COMMAND = 1
MESSAGE_ACK = 2
MESSAGE_ERROR = 3
MESSAGE_HEARTBEAT = 4

FLAG_EMERGENCY_STOP = 0x01
KNOWN_FLAGS = FLAG_EMERGENCY_STOP

HEADER_FORMAT = ">2sBBIBB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
CRC_FORMAT = ">H"
CRC_SIZE = struct.calcsize(CRC_FORMAT)
MAX_PAYLOAD_BYTES = 255

COMMAND_PAYLOAD_FORMAT = ">BBHB"
COMMAND_PAYLOAD_SIZE = struct.calcsize(COMMAND_PAYLOAD_FORMAT)
ACK_PAYLOAD_FORMAT = ">B"
ACK_PAYLOAD_SIZE = struct.calcsize(ACK_PAYLOAD_FORMAT)

ACTION_TO_CODE = {
    "stop": 0,
    "forward": 1,
    "backward": 2,
    "left": 3,
    "right": 4,
}
CODE_TO_ACTION = {value: key for key, value in ACTION_TO_CODE.items()}

WHEEL_MODE_TO_CODE = {
    "ordinary": 1,
    "mecanum": 2,
}
CODE_TO_WHEEL_MODE = {value: key for key, value in WHEEL_MODE_TO_CODE.items()}

STATUS_TO_CODE = {
    "accepted": 1,
    "rejected": 2,
    "executed": 3,
    "timeout": 4,
}
CODE_TO_STATUS = {value: key for key, value in STATUS_TO_CODE.items()}

ERROR_TO_CODE = {
    "invalid_packet": 1,
    "invalid_command": 2,
    "unsupported_version": 3,
    "crc_mismatch": 4,
    "internal_error": 5,
}
CODE_TO_ERROR = {value: key for key, value in ERROR_TO_CODE.items()}


class DectPacketError(ValueError):
    pass


@dataclass(frozen=True)
class DectCommandPacket:
    sequence_id: int
    command: MotionCommand
    emergency_stop: bool = False

    def encode(self) -> bytes:
        command = self.command.normalized()
        if self.emergency_stop and command.action != "stop":
            raise DectPacketError("emergency_stop packets must use the stop action.")

        action_code = _lookup_code(ACTION_TO_CODE, command.action, "action")
        wheel_mode_code = _lookup_code(WHEEL_MODE_TO_CODE, command.wheel_mode, "wheel_mode")
        payload = struct.pack(
            COMMAND_PAYLOAD_FORMAT,
            action_code,
            command.speed,
            command.duration_ms,
            wheel_mode_code,
        )
        flags = FLAG_EMERGENCY_STOP if self.emergency_stop else 0
        return _frame(MESSAGE_COMMAND, self.sequence_id, flags, payload)


@dataclass(frozen=True)
class DectAckPacket:
    sequence_id: int
    status: str = "accepted"

    def encode(self) -> bytes:
        status_code = _lookup_code(STATUS_TO_CODE, self.status, "status")
        payload = struct.pack(ACK_PAYLOAD_FORMAT, status_code)
        return _frame(MESSAGE_ACK, self.sequence_id, 0, payload)


@dataclass(frozen=True)
class DectErrorPacket:
    sequence_id: int
    code: str
    message: str

    def encode(self) -> bytes:
        code_value = _lookup_code(ERROR_TO_CODE, self.code, "error code")
        message_bytes = self.message.encode("utf-8")
        if len(message_bytes) > MAX_PAYLOAD_BYTES - 2:
            raise DectPacketError("error message is too long for one packet.")
        payload = bytes((code_value, len(message_bytes))) + message_bytes
        return _frame(MESSAGE_ERROR, self.sequence_id, 0, payload)


@dataclass(frozen=True)
class DectHeartbeatPacket:
    sequence_id: int

    def encode(self) -> bytes:
        return _frame(MESSAGE_HEARTBEAT, self.sequence_id, 0, b"")


DectPacket = Union[DectCommandPacket, DectAckPacket, DectErrorPacket, DectHeartbeatPacket]


def encode_motion_command(
    command: MotionCommand,
    sequence_id: int,
    emergency_stop: bool = False,
) -> bytes:
    return DectCommandPacket(
        sequence_id=sequence_id,
        command=command,
        emergency_stop=emergency_stop,
    ).encode()


def encode_ack(sequence_id: int, status: str = "accepted") -> bytes:
    return DectAckPacket(sequence_id=sequence_id, status=status).encode()


def encode_error(sequence_id: int, code: str, message: str) -> bytes:
    return DectErrorPacket(sequence_id=sequence_id, code=code, message=message).encode()


def encode_heartbeat(sequence_id: int) -> bytes:
    return DectHeartbeatPacket(sequence_id=sequence_id).encode()


def decode_motion_command(frame: bytes) -> MotionCommand:
    packet = decode_packet(frame)
    if not isinstance(packet, DectCommandPacket):
        raise DectPacketError("packet is not a motion command.")
    return packet.command


def decode_packet(frame: bytes) -> DectPacket:
    if len(frame) < HEADER_SIZE + CRC_SIZE:
        raise DectPacketError("packet is shorter than the DECTmo header.")

    body = frame[:-CRC_SIZE]
    expected_crc = struct.unpack(CRC_FORMAT, frame[-CRC_SIZE:])[0]
    actual_crc = _crc16(body)
    if actual_crc != expected_crc:
        raise DectPacketError("packet CRC mismatch.")

    magic, version, message_type, sequence_id, flags, payload_size = struct.unpack(
        HEADER_FORMAT,
        body[:HEADER_SIZE],
    )
    if magic != MAGIC:
        raise DectPacketError("invalid DECTmo packet magic.")
    if version != PACKET_VERSION:
        raise DectPacketError(f"unsupported packet version: {version}")
    if flags & ~KNOWN_FLAGS:
        raise DectPacketError(f"unsupported packet flags: {flags:#04x}")

    payload = body[HEADER_SIZE:]
    if payload_size != len(payload):
        raise DectPacketError("packet payload length does not match header.")

    if message_type == MESSAGE_COMMAND:
        return _decode_command(sequence_id, flags, payload)
    if message_type == MESSAGE_ACK:
        return _decode_ack(sequence_id, flags, payload)
    if message_type == MESSAGE_ERROR:
        return _decode_error(sequence_id, flags, payload)
    if message_type == MESSAGE_HEARTBEAT:
        return _decode_heartbeat(sequence_id, flags, payload)

    raise DectPacketError(f"unsupported message type: {message_type}")


def _decode_command(sequence_id: int, flags: int, payload: bytes) -> DectCommandPacket:
    if len(payload) != COMMAND_PAYLOAD_SIZE:
        raise DectPacketError("command payload has invalid length.")

    action_code, speed, duration_ms, wheel_mode_code = struct.unpack(COMMAND_PAYLOAD_FORMAT, payload)
    action = _lookup_value(CODE_TO_ACTION, action_code, "action")
    wheel_mode = _lookup_value(CODE_TO_WHEEL_MODE, wheel_mode_code, "wheel_mode")
    emergency_stop = bool(flags & FLAG_EMERGENCY_STOP)
    if emergency_stop and action != "stop":
        raise DectPacketError("emergency_stop flag is only valid for stop commands.")

    try:
        command = MotionCommand.from_dict(
            {
                "id": str(sequence_id),
                "source": "remote-dect",
                "action": action,
                "speed": speed,
                "duration_ms": duration_ms,
                "wheel_mode": wheel_mode,
            }
        )
    except MotionProtocolError as exc:
        raise DectPacketError(f"invalid motion command: {exc}") from exc

    return DectCommandPacket(
        sequence_id=sequence_id,
        command=command,
        emergency_stop=emergency_stop,
    )


def _decode_ack(sequence_id: int, flags: int, payload: bytes) -> DectAckPacket:
    if flags:
        raise DectPacketError("ack packets do not support flags.")
    if len(payload) != ACK_PAYLOAD_SIZE:
        raise DectPacketError("ack payload has invalid length.")

    (status_code,) = struct.unpack(ACK_PAYLOAD_FORMAT, payload)
    return DectAckPacket(
        sequence_id=sequence_id,
        status=_lookup_value(CODE_TO_STATUS, status_code, "status"),
    )


def _decode_error(sequence_id: int, flags: int, payload: bytes) -> DectErrorPacket:
    if flags:
        raise DectPacketError("error packets do not support flags.")
    if len(payload) < 2:
        raise DectPacketError("error payload has invalid length.")

    code_value = payload[0]
    message_size = payload[1]
    message_bytes = payload[2:]
    if message_size != len(message_bytes):
        raise DectPacketError("error message length does not match payload.")

    try:
        message = message_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DectPacketError("error message is not valid UTF-8.") from exc

    return DectErrorPacket(
        sequence_id=sequence_id,
        code=_lookup_value(CODE_TO_ERROR, code_value, "error code"),
        message=message,
    )


def _decode_heartbeat(sequence_id: int, flags: int, payload: bytes) -> DectHeartbeatPacket:
    if flags:
        raise DectPacketError("heartbeat packets do not support flags.")
    if payload:
        raise DectPacketError("heartbeat payload must be empty.")
    return DectHeartbeatPacket(sequence_id=sequence_id)


def _frame(message_type: int, sequence_id: int, flags: int, payload: bytes) -> bytes:
    _validate_uint("sequence_id", sequence_id, 0xFFFFFFFF)
    _validate_uint("flags", flags, 0xFF)
    if flags & ~KNOWN_FLAGS:
        raise DectPacketError(f"unsupported packet flags: {flags:#04x}")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise DectPacketError("payload is too large for one packet.")

    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        PACKET_VERSION,
        message_type,
        sequence_id,
        flags,
        len(payload),
    )
    body = header + payload
    return body + struct.pack(CRC_FORMAT, _crc16(body))


def _crc16(data: bytes) -> int:
    return binascii.crc_hqx(data, 0xFFFF)


def _validate_uint(field_name: str, value: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DectPacketError(f"{field_name} must be an integer.")
    if not 0 <= value <= maximum:
        raise DectPacketError(f"{field_name} must be between 0 and {maximum}.")


def _lookup_code(mapping: dict[str, int], value: str, field_name: str) -> int:
    try:
        return mapping[value]
    except KeyError as exc:
        raise DectPacketError(f"unsupported {field_name}: {value}") from exc


def _lookup_value(mapping: dict[int, str], value: int, field_name: str) -> str:
    try:
        return mapping[value]
    except KeyError as exc:
        raise DectPacketError(f"unsupported {field_name} code: {value}") from exc
