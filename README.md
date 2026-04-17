# DECTmo

DECTmo is a Raspberry Pi 5 vehicle-control and live-video platform for a Freenove 4WD car. The current system uses the Pi 5 as the main controller, a Raspberry Pi Pico as the motor executor, and a browser control surface over the same WiFi network. The next major goal is to replace the local network command path with an nRF9151 / DECT NR+ transport while keeping the same motion standard.

The project is being built in small, tested phases: first reliable Pi-to-Pico control, then browser driving and camera streaming, then standardized command packets, and finally real DECT NR+ radio integration.

## Current Baseline

The following parts have been brought up and verified:

- Raspberry Pi 5 running Raspberry Pi OS (64-bit).
- Pico connected to the Pi 5 over USB as `/dev/ttyACM0`.
- Pico running `control/pico_micropython_bridge/main.py` as `main.py`.
- Pi-to-Pico serial health checks returning `PONG`.
- Freenove motor movement through the Pico bridge.
- Forward/backward polarity corrected in the bridge.
- Browser control routed through the Pi motion standard.
- `W`, `A`, `S`, `D`, arrow-key, and button movement from another same-WiFi computer.
- USB camera live stream exposed by the Pi browser server.
- Motion sequences and validation tests for repeatable movement checks.
- DECT command packet v1 defined and covered by encode/decode tests.
- nRF9151 USB modem/application port identified as `/dev/ttyACM1`, responding to `AT` and `AT+CGMR` with modem firmware `mfw_nrf91x1_2.0.4`.

Left/right movement is intentionally still marked for real-world tuning. The current ordinary-wheel behavior is a gentle pivot: one side stops while the other side moves at 65% of the requested speed.

## Architecture

```text
Browser controls
Local motion sequences
Future DECT NR+ receiver
        |
        v
Pi 5 motion standard
        |
        v
USB serial /dev/ttyACM0
        |
        v
Pico MicroPython bridge
        |
        v
Freenove motor driver and wheels

USB camera
        |
        v
Pi 5 video service
        |
        v
Browser MJPEG stream now
Future DECT NR+ video path later
```

The Pi 5 is the vehicle brain. The Pico should stay focused on safe, timed motor execution. Remote control sources, browser input, local sequences, and future DECT packets all enter through the same Pi motion contract before anything reaches the Pico.

## Motion Standard

All movement commands should use the v1 logical command format documented in `docs/motion-standard.md`.

V1 actions:

| Action | Meaning |
| --- | --- |
| `stop` | Stop immediately. |
| `forward` | Move physically forward. |
| `backward` | Move physically backward. |
| `left` | Turn left while standing still. |
| `right` | Turn right while standing still. |

Movement commands use:

- `speed`: `1` to `100` for movement.
- `duration_ms`: `1` to `5000` for timed movement pulses.
- `wheel_mode`: usually `ordinary` for the current Freenove build.
- `stop`: normalized to `speed = 0` and `duration_ms = 0`.

The Pi converts validated logical commands into Pico serial commands such as:

```text
PING
S
F 50 250
B 50 250
DRIVE 0 32 250
DRIVE 32 0 250
```

Future nRF9151 / DECT NR+ command packets should preserve the same fields even if the transport payload becomes compact binary instead of JSON.

## Hardware Setup

Use a data-capable USB-A to Micro-B cable:

```text
Raspberry Pi 5 USB-A port  ->  Raspberry Pi Pico micro-USB port
```

The USB cable is enough for Pico power and serial communication. The Freenove battery pack is required for motor movement. Do not power the motors from the Raspberry Pi 5 USB port, and do not connect the motor driver directly to Pi GPIO.

Recommended OS for the Pi 5:

- Use **Raspberry Pi OS (64-bit)**.
- Use Desktop for easier first bring-up with a local browser.
- Use Lite later if the Pi will run headless over SSH.
- Do not use Raspberry Pi Desktop; that image is for PC/Mac hardware.

## Quick Start On The Pi 5

```bash
cd ~/Desktop/DECTmo
git pull --ff-only
```

Install the Pi-side dependencies:

```bash
sudo apt update
sudo apt install -y python3-serial python3-opencv v4l-utils
```

Upload the MicroPython bridge to the Pico when needed:

```bash
python3 control/pi5_controller/upload_micropython_bridge.py --port /dev/ttyACM0
```

Verify serial control:

```bash
python3 control/pi5_controller/diagnose_serial.py --port /dev/ttyACM0
```

Expected bridge output includes:

```text
READY micropython_serial_bridge
INFO bridge=micropython_serial_bridge version=1.1.0 motor_direction=-1
PONG
OK STOP
OK MOVE
OK AUTO_STOP
```

Verify the nRF9151 USB modem/application port:

```bash
python3 control/pi5_controller/diagnose_nrf_modem.py
```

Start the browser controller with camera streaming:

```bash
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --wheel-mode ordinary --host 0.0.0.0 --http-port 8000 --camera-device /dev/video0
```

Open from another computer on the same WiFi:

```text
http://<raspberry-pi-ip>:8000
```

The browser supports:

| Input | Action |
| --- | --- |
| W or Up | Forward |
| S or Down | Backward |
| A or Left | Left |
| D or Right | Right |
| Space | Stop |

## Sequence Checks

List available movement sequences:

```bash
python3 control/pi5_controller/sequence_runner.py --list
```

Validate a sequence without moving the car:

```bash
python3 control/pi5_controller/sequence_runner.py direction_check
```

Run a real low-risk movement test with the car lifted:

```bash
python3 control/pi5_controller/sequence_runner.py direction_check --execute --port /dev/ttyACM0 --speed 15
```

## Development Checks

Run these before committing code changes:

```bash
python -m compileall control tests
python -m unittest discover -s tests
```

Docs-only changes should still keep the repository clean and should be committed as their own iteration.

## Project Layout

```text
control/pico_micropython_bridge/  Active MicroPython bridge copied to Pico main.py
control/pi5_controller/           Pi-side serial, motion, web, camera, and sequence code
control/pi5_controller/sequences/ Predefined movement checks
docs/bringup-checklist.md         First hardware and SSH bring-up flow
docs/dect-command-packet-v1.md    Compact command packet for future nRF9151 transport
docs/nrf9151-firmware-flashing.md Local Nordic firmware flashing notes
docs/nrf9151-bringup.md           nRF9151 USB modem port diagnosis
docs/pi5-pico-usb-control.md      USB control and Freenove motor notes
docs/remote-control-and-video.md  Same-WiFi browser control and USB camera flow
docs/motion-standard.md           Canonical motion command contract
tests/                            Protocol validation tests
```

The Freenove vendor package is intentionally ignored by Git. Keep it local when referencing the original tutorials and sketches, but do not commit `Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico-main/`.

## Next Phases

1. Finish movement calibration for ordinary wheels, especially left/right turning behavior.
2. Confirm both nRF9151 boards can expose a DECT NR+ payload path, starting from the verified `/dev/ttyACM1` AT port on the Pi-side board.
3. Build the Pi-side nRF serial adapter around the DECTmo packet bytes once that payload path is available.
4. Prove real command delivery over the actual DECT NR+ path with heartbeat, emergency `STOP`, and one short movement command.
5. Define and test low-quality live video packetization after command reliability is stable.
6. Revisit H.264 or another compressed video path once the radio throughput and latency are measured.

Do not add fake DECT transport behavior as a substitute for radio validation. Local packet encode/decode tests are useful, but transport behavior must be proven with the actual nRF9151 boards.

Nordic firmware bundles such as `nrf9151dk_mfw-2.0.4_sdk-3.2.1/` are local vendor downloads and are ignored by Git.
