# Motion Standard

The Pi 5 is the vehicle brain. Every command source must use the same logical movement standard:

```text
web UI now -> Pi motion standard -> Pico USB bridge -> motors
DECT later -> Pi motion standard -> Pico USB bridge -> motors
```

## V1 Actions

| Action | Meaning |
| --- | --- |
| `stop` | Stop immediately. |
| `forward` | Move physically forward. |
| `backward` | Move physically backward. |
| `left` | Turn left in place while standing still. |
| `right` | Turn right in place while standing still. |

Curved movement is not part of v1. It can be added later as a separate action family.

## Speed

Movement commands carry `speed` from `1` to `100`.

`speed` is a normalized percentage-like value passed to the Pico bridge. It is not meters per second. Calibration to real speed or distance will come later.

`stop` always normalizes to:

```json
{"action": "stop", "speed": 0, "duration_ms": 0}
```

## Duration

Movement commands carry `duration_ms` from `1` to `5000`.

Each movement step is timed. Sequence execution waits for the current step duration before sending the next step. This keeps behavior predictable and easy to debug.

## Command JSON

This is the canonical logical command format that the remote side should eventually send through nRF9151 and DECT NR+ to the Pi 5:

```json
{
  "version": 1,
  "type": "motion.command",
  "id": "cmd-000001",
  "source": "remote-dect",
  "action": "forward",
  "speed": 35,
  "duration_ms": 300,
  "wheel_mode": "ordinary"
}
```

The Pi validates this command before it can reach the Pico.

## Ack JSON

```json
{
  "version": 1,
  "type": "motion.ack",
  "id": "cmd-000001",
  "status": "accepted"
}
```

## Error JSON

```json
{
  "version": 1,
  "type": "motion.error",
  "id": "cmd-000001",
  "code": "invalid_speed",
  "message": "speed must be between 0 and 100"
}
```

## Sequence JSON

Sequences are predefined local movement scripts. They are useful for testing and for emulating future DECT commands before the nRF9151 link is integrated.

```json
{
  "version": 1,
  "type": "motion.sequence",
  "id": "direction-check",
  "name": "Forward, backward, left, right check",
  "default_speed": 20,
  "wheel_mode": "ordinary",
  "steps": [
    {"action": "forward", "duration_ms": 250},
    {"action": "stop"},
    {"action": "backward", "duration_ms": 250},
    {"action": "stop"},
    {"action": "left", "duration_ms": 250},
    {"action": "stop"},
    {"action": "right", "duration_ms": 250},
    {"action": "stop"}
  ]
}
```

## Running Sequences

List built-in sequences:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/sequence_runner.py --list
```

Dry-run validation, which does not move the car:

```bash
python3 control/pi5_controller/sequence_runner.py direction_check
```

Real execution, with the car lifted:

```bash
python3 control/pi5_controller/sequence_runner.py direction_check --execute --port /dev/ttyACM0
```

Override speed for all movement steps:

```bash
python3 control/pi5_controller/sequence_runner.py direction_check --execute --port /dev/ttyACM0 --speed 15
```

## DECT NR+ Mapping Later

JSON is the current human-readable standard. For the real DECT transport, the payload can be converted into a compact binary packet, but it must preserve the same fields:

```text
version
type
id / sequence number
action
speed
duration_ms
wheel_mode
```

Commands are reliable and acknowledged. Video is separate and best-effort. Emergency stop must always have priority over video traffic.
