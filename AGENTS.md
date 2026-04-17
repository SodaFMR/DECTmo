# DECTmo Project Notes

These notes are the working contract for this repository.

## Operating Rules

- Commit and push every intentional repo change before ending a work iteration.
- Use Conventional Commit prefixes, for example `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, or `chore:`.
- Keep the Freenove vendor package local and ignored.
- Keep Nordic firmware bundles local and ignored.
- Prefer small, understandable modules over many specialized scripts.
- Keep hardware-facing tests safe: dry-run first, then lifted-car tests, then floor tests.

## Current Scope

The active scope is car control and live camera feed.

DECT/nRF work is intentionally on hold. Do not add DECT transport code back into the active path until the car control modules are stable and the real transport API is known.

## Current Verified Baseline

- Raspberry Pi 5 is the main controller and web host.
- Raspberry Pi Pico receives USB serial commands and drives the Freenove motors.
- Pico appears on the Pi as `/dev/ttyACM0`.
- Pico runs `control/pico_micropython_bridge/main.py`.
- Freenove motor movement works.
- Forward/backward physical direction has been corrected.
- Same-WiFi browser control works from another computer.
- USB camera streaming works through the browser server.

## Lego Module Layout

```text
control/pi5_controller/car.py
  Core car API, movement validation, serial connection, and Pico command mapping.

control/pi5_controller/movement_programs.py
  Hardcoded reusable movement programs plus JSON movement loading.

control/pi5_controller/run_movements.py
  CLI runner for dry-run and lifted-car movement tests.

control/pi5_controller/web_control.py
  Browser movement controls and live camera stream.

control/pi5_controller/camera_stream.py
  USB camera helper.

control/pi5_controller/upload_micropython_bridge.py
  Pico bridge upload helper.

control/pico_micropython_bridge/main.py
  Pico firmware.
```

## Movement Contract

Use the simple car API:

```python
car.send_move(action="forward", duration_ms=250, speed=50)
car.send_move(action="left", duration_ms=250, speed=30)
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

Aliases like `w`, `a`, `s`, `d`, `back`, and `backwards` are normalized in `car.py`.

## Wheel Mode

`wheel_mode` is an internal/default car setting.

- `ordinary`: current Freenove car. `left` and `right` turn.
- `mecanum`: only for mecanum wheels. `left` and `right` strafe.

Use `ordinary` for the current car unless the physical wheels change.

## Safety

- Do not power motors from the Pi USB port.
- Do not connect the Freenove motor driver directly to Pi GPIO.
- The Pico bridge has timed movement and failsafe stop behavior.
- The web UI sends repeated short movement pulses and sends stop on key release or focus loss.
- Keep left/right calibration separate from code structure work.

## Useful Commands

Start the web UI:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --host 0.0.0.0 --http-port 8000 --camera-device /dev/video0
```

List movement programs:

```bash
python3 control/pi5_controller/run_movements.py --list
```

Dry-run a movement:

```bash
python3 control/pi5_controller/run_movements.py direction_check
```

Execute a movement with the car lifted:

```bash
python3 control/pi5_controller/run_movements.py direction_check --execute --port /dev/ttyACM0 --speed 15
```

Run repository checks:

```bash
python -m compileall control tests
python -m unittest discover -s tests
```

## Next Work

1. Keep the simple car/web/camera path stable.
2. Tune left/right turning physically.
3. Add more movement programs only when they help testing.
4. Add a future communication adapter only after the real transport API is known.
