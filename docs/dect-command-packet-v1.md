# DECT Command Packet V1

This document defines the first compact packet format for sending DECTmo motion commands through the nRF9151 / DECT NR+ path.

The packet layer is only a byte contract. It does not emulate radio behavior. Transport behavior must be proven later with the real nRF9151 boards.

## Transport Role

The intended command path is:

```text
remote controller
        -> DECTmo packet bytes
        -> remote nRF9151
        -> DECT NR+
        -> Pi-side nRF9151
        -> Pi 5 packet decoder
        -> Pi motion standard
        -> Pico USB bridge
        -> motors
```

The packet must decode into the logical `motion.command` standard from `docs/motion-standard.md`. Remote-side code should not send raw Pico commands.

## Frame Layout

All multi-byte integers are unsigned big-endian.

```text
offset  size  field
0       2     magic, ASCII "DM"
2       1     packet version, currently 1
3       1     message type
4       4     sequence_id
8       1     flags
9       1     payload length in bytes
10      N     payload
10+N    2     CRC-16/CCITT over header + payload
```

Maximum payload size is 255 bytes.

## Message Types

| Code | Type |
| ---: | --- |
| `1` | Command |
| `2` | Ack |
| `3` | Error |
| `4` | Heartbeat |

## Flags

| Bit | Name | Meaning |
| ---: | --- | --- |
| `0` | Emergency stop | This command is a priority stop command. |

Reserved bits must be zero. Emergency stop is only valid on a `stop` command.

## Command Payload

```text
offset  size  field
0       1     action
1       1     speed
2       2     duration_ms
4       1     wheel_mode
```

Action codes:

| Code | Action |
| ---: | --- |
| `0` | `stop` |
| `1` | `forward` |
| `2` | `backward` |
| `3` | `left` |
| `4` | `right` |

Wheel mode codes:

| Code | Wheel mode |
| ---: | --- |
| `1` | `ordinary` |
| `2` | `mecanum` |

Command values keep the same rules as the motion standard:

- Movement speed is `1-100`.
- Movement duration is `1-5000` ms.
- Stop normalizes to speed `0` and duration `0`.

## Ack Payload

```text
offset  size  field
0       1     status
```

Status codes:

| Code | Status |
| ---: | --- |
| `1` | `accepted` |
| `2` | `rejected` |
| `3` | `executed` |
| `4` | `timeout` |

## Error Payload

```text
offset  size  field
0       1     error code
1       1     UTF-8 message length
2       N     UTF-8 message
```

Error codes:

| Code | Error |
| ---: | --- |
| `1` | `invalid_packet` |
| `2` | `invalid_command` |
| `3` | `unsupported_version` |
| `4` | `crc_mismatch` |
| `5` | `internal_error` |

## Heartbeat Payload

Heartbeat packets have an empty payload. They are for no-motor link checks and deadman timing.

## Python Implementation

The local implementation lives in:

```text
control/pi5_controller/dect_packet.py
```

It provides:

```text
encode_motion_command()
decode_motion_command()
decode_packet()
encode_ack()
encode_error()
encode_heartbeat()
```

The test coverage lives in:

```text
tests/test_dect_packet.py
```

These tests verify packet framing, command round trips, emergency stop validation, ack/error/heartbeat round trips, and CRC rejection. They do not validate DECT NR+ radio behavior.

## First Hardware Test Later

The first nRF9151 test should use the packet bytes exactly as defined here:

```text
remote nRF9151 sends command packet
Pi-side nRF9151 receives packet bytes
Pi 5 decodes packet
Pi 5 returns ack packet
```

The first no-motor application check should be a heartbeat packet and ack. The first motor-facing command should be an emergency `stop`, followed by one very short low-speed movement command with the car lifted.
