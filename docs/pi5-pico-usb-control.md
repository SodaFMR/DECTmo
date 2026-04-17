# Raspberry Pi 5 to Pico USB Control

## What The Freenove Code Does

The Freenove ordinary-wheel sketch controls the car with differential speeds:

| Action | Left speed | Right speed |
| --- | ---: | ---: |
| Stop | 0 | 0 |
| Forward | 50 | 50 |
| Backward | -50 | -50 |
| Turn left | -50 | 50 |
| Turn right | 50 | -50 |

The motor pins used by the Freenove board are:

| Motor side | Pico GPIO pins |
| --- | --- |
| Right motor 1 | GP7, GP6 |
| Right motor 2 | GP9, GP8 |
| Left motor 1 | GP18, GP19 |
| Left motor 2 | GP21, GP20 |

The Pico is the board that actually drives the motors. The Raspberry Pi 5 should only send high-level commands over USB serial.

## OS Choice

Install **Raspberry Pi OS (64-bit)** for the Pi 5.

Choose:

| Image | Use it? | Reason |
| --- | --- | --- |
| Raspberry Pi OS (64-bit) | Yes | Best default for Raspberry Pi 5 and this project. |
| Raspberry Pi OS (32-bit) | Avoid | Works on many Pi boards, but there is no advantage here. |
| Raspberry Pi OS (Legacy, 64-bit) | Avoid | Legacy images target older Debian releases and are not the right default for Pi 5 bring-up. |
| Raspberry Pi OS (Legacy, 32-bit) | Avoid | Older compatibility target, not useful for this setup. |
| Raspberry Pi Desktop | No | This is for PC/Mac, not for the Pi 5 board. |

Desktop vs Lite: Desktop is easier for first bring-up because you can use the local browser UI. Lite is fine later if the Pi will run headless over SSH.

## Hardware Connection

Use one data-capable USB cable:

```text
Pi 5 USB-A  ->  Pico micro-USB
```

The Pico will appear on the Pi as a serial device, usually `/dev/ttyACM0`.

Keep the Freenove battery pack connected and switched on for the motors. The Pi 5 USB port should not be used as the motor power source.

## Install The Pico Bridge

The current verified Pico path is MicroPython. The Pi-side upload helper copies `control/pico_micropython_bridge/main.py` to the Pico as `main.py`:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/upload_micropython_bridge.py --port /dev/ttyACM0
python3 control/pi5_controller/diagnose_serial.py --port /dev/ttyACM0
```

The bridge accepts newline-terminated USB serial commands:

```text
F 50 250       forward at speed 50 for 250 ms
B 50 250       backward at speed 50 for 250 ms
L 50 250       ordinary-wheel left turn
R 50 250       ordinary-wheel right turn
ML 50 250      mecanum strafe left
MR 50 250      mecanum strafe right
S              stop immediately
DRIVE 50 -50 250    raw differential left/right speeds for 250 ms
WHEEL 50 50 50 50 250   raw four-wheel speeds for 250 ms
PING           health check
```

The bridge also has a failsafe: if serial commands stop arriving, the motors stop automatically.

## Run From The Pi 5

Install serial support:

```bash
sudo apt update
sudo apt install -y python3-serial
```

Find the Pico serial port:

```bash
python3 -m serial.tools.list_ports
```

Run keyboard control:

```bash
python3 control/pi5_controller/keyboard_control.py --port /dev/ttyACM0 --wheel-mode ordinary
```

Controls:

| Key | Action |
| --- | --- |
| W or Up | Forward |
| S or Down | Backward |
| A or Left | Left |
| D or Right | Right |
| Space | Stop |
| + / - | Change speed |
| Q | Quit |

Run browser control:

```bash
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --wheel-mode ordinary --host 0.0.0.0 --http-port 8000
```

Open:

```text
http://<raspberry-pi-ip>:8000
```

Use `--wheel-mode mecanum` only if your kit is assembled with mecanum wheels and you want left/right to strafe instead of turning.
