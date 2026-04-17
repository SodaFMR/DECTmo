# DECTmo

DECTmo is now focused on one clear job: use a Raspberry Pi 5 to control a Freenove 4WD car through a Raspberry Pi Pico, with a browser UI and live USB camera feed.

The current active scope intentionally ignores DECT/nRF work. That work can return later as a communication adapter, but the car code should stay simple: one module moves the car, one module defines reusable movements, one web server exposes control and video.

## Current Baseline

- Raspberry Pi 5 is the main controller.
- Raspberry Pi Pico is connected over USB, usually as `/dev/ttyACM0`.
- The Pico runs `control/pico_micropython_bridge/main.py`.
- The Freenove car moves through the Pico bridge.
- Forward/backward direction is corrected in the Pico bridge.
- Browser control works from the same WiFi.
- The web UI supports buttons, `W/A/S/D`, arrow keys, speed, and stop.
- USB camera live feed works in the same web UI.

## Simple Architecture

```text
Browser UI
        |
        v
control/pi5_controller/web_control.py
        |
        v
control/pi5_controller/car.py
        |
        v
USB serial /dev/ttyACM0
        |
        v
Pico MicroPython bridge
        |
        v
Freenove motors

USB camera
        |
        v
control/pi5_controller/camera_stream.py
        |
        v
Browser MJPEG stream
```

## Lego Modules

```text
control/pi5_controller/car.py
  Movement data object, Pico serial connection, action validation, and Pico command mapping.

control/pi5_controller/movement_programs.py
  Small hardcoded movement programs and JSON movement loading.

control/pi5_controller/run_movements.py
  CLI to execute movement programs and JSON movement files, with a dry-run option.

control/pi5_controller/web_control.py
  Browser controller with live camera stream.

control/pi5_controller/camera_stream.py
  USB camera capture and JPEG encoding.

control/pi5_controller/upload_micropython_bridge.py
  Helper to upload the MicroPython bridge to the Pico when needed.

control/pico_micropython_bridge/main.py
  Pico firmware that receives serial commands and drives the motors.
```

## Movement API

The core API should feel like this:

```python
car.send_move(action="forward", duration_ms=250, speed=34)
car.send_move(action="left", duration_ms=250, speed=34)
car.send_move(action="backward", duration_ms=250, speed=34)
car.stop()
```

Supported actions:

```text
forward
backward
left
right
stop
```

Aliases like `w`, `a`, `s`, `d`, `back`, and `backwards` are normalized by `car.py`.

## Wheel Mode

`wheel_mode` is now an internal/default car setting, not something every movement has to care about.

- `ordinary`: the current Freenove setup. `left` and `right` turn the car.
- `mecanum`: only for mecanum wheels. `left` and `right` strafe sideways.

For the current car, use the default:

```text
ordinary
```

In `ordinary` mode, `left` and `right` use the requested speed on the forward-moving side and a small reverse speed on the opposite side. With speed `34`, the Pico command is:

```text
left  -> DRIVE -28 34 250
right -> DRIVE 34 -28 250
```

The reverse side is capped at `28`, and also capped by the requested speed for low-speed tests.

## Run The Web UI

On the car Pi:

```bash
cd ~/Desktop/DECTmo
git pull --ff-only
python3 control/pi5_controller/web_control.py
```

Open from another computer on the same WiFi:

```text
http://192.168.0.167:8000
```

Without camera:

```bash
python3 control/pi5_controller/web_control.py --no-camera
```

Default web values:

```text
Pico serial port: auto-detected, usually /dev/ttyACM0
host: 0.0.0.0
HTTP port: 8000
camera: /dev/video0
wheel mode: ordinary
movement pulse: 250 ms
```

## Run Movement Programs

List available movement programs and JSON files:

```bash
python3 control/pi5_controller/run_movements.py --list
```

Execute the default `direction_check` movement:

```bash
python3 control/pi5_controller/run_movements.py
```

Execute another movement:

```bash
python3 control/pi5_controller/run_movements.py test_1
python3 control/pi5_controller/run_movements.py direction_check --speed 20
```

Dry-run without moving the car:

```bash
python3 control/pi5_controller/run_movements.py --dry-run
python3 control/pi5_controller/run_movements.py test_1 --dry-run
```

The old `--execute` flag is still accepted, but it is no longer required.

For any execution test, keep the car lifted until the movement is confirmed.

```bash
python3 control/pi5_controller/run_movements.py direction_check --speed 20
```

Default movement values:

```text
program: direction_check
Pico serial port: auto-detected, usually /dev/ttyACM0
speed: from the movement JSON, currently 34 for the built-in JSON files
duration: from the movement JSON, usually 250 ms
gap: 300 ms
```

Movement execution is automatic. Use `--dry-run` when you only want to print the plan.

## JSON Movement Files

Movement files live in:

```text
control/pi5_controller/movements/
```

Example:

```json
{
  "name": "Short forward movement",
  "default_speed": 34,
  "default_duration_ms": 250,
  "movements": [
    {"action": "forward"},
    {"action": "stop", "duration_ms": 100}
  ]
}
```

## Development Checks

```bash
python -m compileall control tests
python -m unittest discover -s tests
```

## Local Vendor Files

Keep vendor downloads local and ignored:

```text
Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico-main/
nrf9151dk_mfw-*_sdk-*/
```
