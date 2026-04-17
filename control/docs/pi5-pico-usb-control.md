# Pi 5 To Pico Car Control

The Raspberry Pi 5 sends simple serial commands to the Pico. The Pico drives the Freenove motors.

```text
Pi 5 web UI or movement program
        -> car.py
        -> USB serial /dev/ttyACM0
        -> Pico MicroPython bridge
        -> Freenove motors
```

## Hardware

Use a data-capable USB cable:

```text
Pi 5 USB-A  ->  Pico micro-USB
```

The USB cable powers the Pico and carries serial commands. The Freenove battery pack powers the motors.

## Pico Bridge

The active Pico firmware is:

```text
control/pico_micropython_bridge/main.py
```

Upload it when needed:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/upload_micropython_bridge.py --port /dev/ttyACM0
```

## Car API

Use `control/pi5_controller/car.py` as the movement API:

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

## Wheel Mode

`wheel_mode` tells `car.py` how to translate `left` and `right`.

- `ordinary`: normal Freenove wheels. `left` and `right` turn the car.
- `mecanum`: mecanum wheels. `left` and `right` strafe sideways.

The current car uses `ordinary`.

## Web UI

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --host 0.0.0.0 --http-port 8000 --camera-device /dev/video0
```

Open:

```text
http://192.168.0.167:8000
```

## Movement Programs

```bash
python3 control/pi5_controller/run_movements.py --list
python3 control/pi5_controller/run_movements.py direction_check
python3 control/pi5_controller/run_movements.py direction_check --execute --port /dev/ttyACM0 --speed 15
```

The default mode is dry-run. Use `--execute` only when the car is lifted or you are ready for movement.
