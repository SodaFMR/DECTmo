# DECTmo Project Notes

These notes are the persistent working contract for future development sessions in this repository.

## Operating Rules

- Commit and push every intentional repo change before ending a work iteration.
- Use Conventional Commit prefixes, for example `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, or `chore:`.
- Keep changes small and testable. Prefer one verified phase per commit.
- Keep the Freenove vendor package local and ignored. Do not commit `Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico-main/`.
- Keep Nordic firmware bundles local and ignored. Do not commit `nrf9151dk_mfw-*_sdk-*/`.
- The Raspberry Pi 5 project path used during bring-up is `~/Desktop/DECTmo`.
- Before hardware-facing changes, run a no-motor, dry-run, or lifted-car test whenever possible.

## Current Verified Baseline

- Raspberry Pi 5 is running Raspberry Pi OS (64-bit).
- Pico appears on the Pi 5 as `/dev/ttyACM0`.
- Pico runs `control/pico_micropython_bridge/main.py` as `main.py`.
- Serial diagnostics return `READY micropython_serial_bridge`, `PONG`, `OK STOP`, `OK MOVE`, and `OK AUTO_STOP`.
- Bridge info should report `version=1.1.0` and `motor_direction=-1`.
- Freenove motor movement works through the Pico bridge.
- Forward and backward physical direction has been corrected.
- Same-WiFi browser control works from another PC.
- Browser control is routed through the Pi motion standard, not directly to raw Pico strings.
- USB camera streaming works through the Pi browser server.
- Local movement sequences and protocol unit tests are available.
- DECT command packet v1 is defined in `docs/dect-command-packet-v1.md` and implemented in `control/pi5_controller/dect_packet.py`.
- Pi-side nRF9151 is visible through SEGGER J-Link and `/dev/ttyACM1` responds to safe `AT` / `AT+CGMR` probes with `mfw_nrf91x1_2.0.4`.
- Local firmware flashing notes for the downloaded `nrf9151dk_mfw-2.0.4_sdk-3.2.1/` bundle live in `docs/nrf9151-firmware-flashing.md`.

## Hardware Roles

- Raspberry Pi 5 is the main controller, network host, future DECT gateway, and video host.
- Raspberry Pi Pico receives USB serial commands and directly drives the Freenove motor pins.
- The Pico should remain a simple motor executor with failsafe stop behavior.
- USB from Pi 5 to Pico is enough for serial and Pico power.
- The Freenove battery pack is required for motor movement.
- Do not power motors from the Pi 5 USB port.
- Do not connect the Freenove motor driver directly to Pi 5 GPIO.

## Architecture Rules

- All command sources must use the Pi motion standard in `docs/motion-standard.md`.
- Web UI, local sequences, keyboard control, and future DECT input must not bypass motion validation.
- The Pi may convert validated motion commands into Pico-specific serial strings.
- Remote-side DECT commands should target the logical motion contract, not raw Pico commands.
- Future nRF9151 command transport should carry the packet bytes from `control/pi5_controller/dect_packet.py`.
- `/dev/ttyACM1` is currently the Pi-side nRF AT modem/application port; `/dev/ttyACM2` did not reply during bring-up.
- Command traffic is reliable and acknowledged.
- Heartbeat packets are the preferred no-motor link check for future nRF9151 bring-up.
- Video traffic is separate and can be best-effort.
- Emergency stop must always have priority over video traffic and queued movement.

## Control Contract

Canonical Pi-side actions:

```text
stop
forward
backward
left
right
```

Movement commands support:

```text
speed:       1-100
duration_ms: 1-5000
wheel_mode:  ordinary or mecanum
```

`stop` normalizes to:

```json
{"action": "stop", "speed": 0, "duration_ms": 0}
```

The Pi then sends newline-terminated commands to the Pico:

```text
PING                 firmware health check
S                    stop
F 50 250             forward at speed 50 for 250 ms
B 50 250             backward at speed 50 for 250 ms
L 50 250             ordinary-wheel left turn, legacy form
R 50 250             ordinary-wheel right turn, legacy form
DRIVE 0 32 250       raw left/right differential speeds for calibrated pivots
DRIVE 32 0 250       raw left/right differential speeds for calibrated pivots
```

Expected bridge replies:

```text
READY micropython_serial_bridge
INFO bridge=micropython_serial_bridge version=1.1.0 motor_direction=-1
PONG
OK STOP
OK MOVE
OK DRIVE
OK AUTO_STOP
```

## Movement Notes

- V1 `left` and `right` mean turning while standing still, not rolling curves.
- Ordinary-wheel `left` and `right` currently use gentle pivot turns.
- The current ordinary-wheel pivot stops one side and moves the other side at 65% of requested speed.
- Left/right turning still needs real-world tuning; do not treat the current calibration as final.
- Curved movement can be added later as a separate action family.

## Product Direction

- Same-WiFi control should continue to work from another computer, including idFelipe, through a browser hosted by the Pi 5.
- Movement controls should support game-style `W`, `A`, `S`, `D`, arrow keys, visible buttons, speed selection, and immediate stop.
- USB camera video should stay available in the same browser control surface.
- Future nRF9151 / DECT NR+ work should first carry motion commands into the same Pi motion standard.
- Use the nRF9151 USB virtual serial path first unless measurement shows it is a bottleneck. SPI can be revisited later.
- Do not fake or mock DECT transport behavior as proof of integration. Packet encode/decode tests are acceptable; radio behavior must be proven with the real nRF9151 boards.

## Code Style

- Keep modules small, direct, and hardware-aware.
- Prefer explicit names over clever abstractions.
- Add comments only when they clarify non-obvious hardware behavior or safety constraints.
- Validate external inputs at the boundary before reaching serial or motor code.
- Keep tests focused on protocol, packet, validation, and mapping behavior.
- Avoid broad refactors while hardware behavior is still being calibrated.
- Remove stale alternate code paths once the project has a verified standard path.

## Useful Commands

Pi-side diagnostics:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/diagnose_serial.py --port /dev/ttyACM0
```

Upload the MicroPython bridge:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/upload_micropython_bridge.py --port /dev/ttyACM0
```

Start browser control with camera:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --wheel-mode ordinary --host 0.0.0.0 --http-port 8000 --camera-device /dev/video0
```

Dry-run a motion sequence:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/sequence_runner.py direction_check
```

Run repository checks:

```bash
python -m compileall control tests
python -m unittest discover -s tests
```

nRF9151 modem-port diagnosis:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/diagnose_nrf_modem.py
```

## Next Implementation Order

1. Keep movement debugging separate from protocol work unless a protocol issue is discovered.
2. Finish ordinary-wheel left/right calibration with lifted-car and floor tests.
3. Confirm both nRF9151 boards can expose a DECT NR+ application payload path.
4. Build the Pi-side nRF serial adapter around the DECTmo packet bytes once that payload path is available.
5. Prove real DECT command delivery between two nRF9151 boards with heartbeat, emergency stop, and one short movement.
6. Only after command reliability is stable, start low-quality video packetization and throughput tests.
