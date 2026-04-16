# Bring-Up Checklist

## 1. Enable `ssh qartia`

This laptop has a local SSH alias configured:

```text
Host qartia
    HostName 192.168.0.167
    User qartia
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

To finish passwordless SSH, authorize this laptop's public key on the Raspberry Pi 5. Run this once from PowerShell on the laptop:

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | ssh qartia@192.168.0.167 "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Enter the Raspberry Pi user's password when SSH asks for it. After that, this should work without a password:

```powershell
ssh qartia "hostname; uname -a"
```

## 2. Check Pico USB Without The Car Batteries

The Pico can be powered by the Pi 5 over the USB-A to micro-USB cable. That is enough to test USB serial and firmware health.

The motors should not be expected to move without the Freenove battery pack. The USB cable is only for Pico power and serial commands; the motor driver needs the car battery.

Run:

```bash
ssh qartia "lsusb; ls -l /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true"
```

Expected result:

```text
/dev/ttyACM0
```

If no serial device appears, try another USB cable. Many micro-USB cables are charge-only.

## 3. Install Pi Dependencies

```bash
ssh qartia "sudo apt update && sudo apt install -y git python3-serial"
```

Clone or update the project on the Pi:

```bash
ssh qartia "test -d ~/DECTmo && git -C ~/DECTmo pull --ff-only || git clone https://github.com/SodaFMR/DECTmo.git ~/DECTmo"
```

## 4. Ping The Pico Firmware

This verifies the flashed bridge sketch is alive, even while the car batteries are still charging:

```bash
ssh qartia "cd ~/DECTmo && python3 - <<'PY'
from control.pi5_controller.serial_car import SerialCar
with SerialCar('/dev/ttyACM0') as car:
    print(car.ping())
PY"
```

Expected:

```text
PONG
```

## 5. First Motor Test After Batteries Are Charged

Put the car on a stand so the wheels cannot drive off the table.

Send a very short low-speed pulse:

```bash
ssh qartia "cd ~/DECTmo && python3 - <<'PY'
import time
from control.pi5_controller.serial_car import SerialCar
with SerialCar('/dev/ttyACM0') as car:
    car.send_move('forward', 25, 200, 'ordinary')
    time.sleep(0.3)
    car.stop()
PY"
```

If the wheels spin backward, the motor polarity is reversed relative to the current firmware. If only one side is reversed, correct the affected motor direction in the Pico bridge before longer tests.

## 6. Run Control UI

Keyboard:

```bash
ssh -t qartia "cd ~/DECTmo && python3 control/pi5_controller/keyboard_control.py --port /dev/ttyACM0 --wheel-mode ordinary"
```

Browser:

```bash
ssh qartia "cd ~/DECTmo && python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --wheel-mode ordinary --host 0.0.0.0 --http-port 8000"
```

Open:

```text
http://192.168.0.167:8000
```
