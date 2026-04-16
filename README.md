# DECTmo

Raspberry Pi 5 to Raspberry Pi Pico USB control for a Freenove 4WD car.

The Freenove vendor package is intentionally ignored by Git. Keep it locally in this repository when you need to reference the original tutorials and sketches, but do not commit it.

## Recommended OS

Use **Raspberry Pi OS (64-bit)** on the Raspberry Pi 5.

Use the normal desktop image if you want to connect a monitor/keyboard and open the browser control page directly on the Pi. Use Lite only if you are comfortable controlling it through SSH. Do not choose Raspberry Pi Desktop for this project; that image is for PC/Mac, not the Raspberry Pi 5.

## Connection

Connect the Raspberry Pi 5 to the Pico with a data-capable USB-A to Micro-B cable:

```text
Raspberry Pi 5 USB-A port  ->  Raspberry Pi Pico micro-USB port
```

The USB cable is for serial commands. Keep the Freenove car battery connected for the motors. Do not power the motors from the Raspberry Pi 5 USB port, and do not connect the motor driver pins directly to the Pi 5 GPIO.

## Project Layout

```text
control/pico_serial_bridge/     Arduino sketch to flash onto the Pico
control/pi5_controller/         Pi 5 keyboard and browser controllers
docs/pi5-pico-usb-control.md    Setup and operating notes
```

## Quick Start

1. Flash `control/pico_serial_bridge/pico_serial_bridge.ino` to the Pico with Arduino IDE.
2. Connect the Pico to the Pi 5 over USB.
3. Follow `docs/bringup-checklist.md` to enable `ssh qartia`, confirm the Pico appears as `/dev/ttyACM0`, and ping the firmware.
4. On the Pi 5, install serial support:

```bash
sudo apt update
sudo apt install -y python3-serial
```

5. Run the keyboard controller:

```bash
python3 control/pi5_controller/keyboard_control.py --wheel-mode ordinary
```

For the browser controller:

```bash
python3 control/pi5_controller/web_control.py --wheel-mode ordinary --host 0.0.0.0 --http-port 8000
```

Then open `http://<raspberry-pi-ip>:8000`.
