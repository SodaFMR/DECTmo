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
  CLI to dry-run or execute movement programs and JSON movement files.

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
car.send_move(action="forward", duration_ms=250, speed=50)
car.send_move(action="left", duration_ms=250, speed=30)
car.send_move(action="backward", duration_ms=250, speed=50)
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

In `ordinary` mode, `left` and `right` use the requested speed on the forward-moving side and a small reverse speed on the opposite side. With speed `50`, the Pico command is:

```text
left  -> DRIVE -28 50 250
right -> DRIVE 50 -28 250
```

The reverse side is capped at `28`, and also capped by the requested speed for low-speed tests.

## Run The Web UI

On the car Pi:

```bash
cd ~/Desktop/DECTmo
git pull --ff-only
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --host 0.0.0.0 --http-port 8000 --camera-device /dev/video0
```

Open from another computer on the same WiFi:

```text
http://192.168.0.167:8000
```

Without camera:

```bash
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --host 0.0.0.0 --http-port 8000 --no-camera
```

## Run Movement Programs

List available movement programs and JSON files:

```bash
python3 control/pi5_controller/run_movements.py --list
```

Dry-run without moving the car:

```bash
python3 control/pi5_controller/run_movements.py test_1
python3 control/pi5_controller/run_movements.py direction_check
```

Execute with the car lifted:

```bash
python3 control/pi5_controller/run_movements.py direction_check --execute --port /dev/ttyACM0 --speed 15
```

## JSON Movement Files

Movement files live in:

```text
control/pi5_controller/movements/
```

Example:

```json
{
  "name": "Short forward movement",
  "default_speed": 20,
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
