# Remote Control And Video

This phase keeps the Raspberry Pi 5 as the main host:

```text
idFelipe or another PC browser -> Pi 5 web server -> USB serial -> Pico motor bridge
USB camera -> Pi 5 web server -> browser MJPEG stream
```

## Phase 1: Network Control Without Camera

Pull the latest project on the Pi:

```bash
cd ~/Desktop/DECTmo
git pull --ff-only
```

Start the web controller without camera streaming:

```bash
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --wheel-mode ordinary --host 0.0.0.0 --http-port 8000 --no-camera
```

From idFelipe or another computer on the same WiFi, open:

```text
http://192.168.0.167:8000
```

No-motor network check from another computer:

```bash
curl http://192.168.0.167:8000/health
```

Expected JSON includes:

```json
{"ok": true, "bridge": "PONG"}
```

The corrected Freenove motor polarity should also appear in `/health`:

```json
{"bridge_info": {"motor_direction": "-1"}}
```

If the value is missing or different, stop the web server, upload the bridge again, and restart the web server:

```bash
python3 control/pi5_controller/upload_micropython_bridge.py --port /dev/ttyACM0
python3 control/pi5_controller/diagnose_serial.py --port /dev/ttyACM0
```

Safe standard-command check from another computer:

```bash
curl -X POST http://192.168.0.167:8000/command \
  -H "Content-Type: application/json" \
  -d '{"action":"stop"}'
```

Expected response:

```json
{
  "version": 1,
  "type": "motion.ack",
  "status": "accepted",
  "dry_run": false,
  "command": {
    "type": "motion.command",
    "source": "web",
    "action": "stop",
    "speed": 0,
    "duration_ms": 0,
    "wheel_mode": "ordinary"
  }
}
```

Browser movement uses the same standard command path. When `W` is held, the browser repeatedly sends `forward` commands with the selected speed and the server validates them as `motion.command` before sending anything to the Pico.

The page supports:

| Input | Action |
| --- | --- |
| W or Up | Forward |
| S or Down | Backward |
| A or Left | Left |
| D or Right | Right |
| Space | Stop |

Keep the car lifted when batteries are connected. Browser key presses send repeated short pulses, and key release sends stop.

## Phase 2: USB Camera Detection

Install camera dependencies on the Pi:

```bash
sudo apt update
sudo apt install -y python3-opencv v4l-utils
```

List camera devices:

```bash
v4l2-ctl --list-devices
ls -l /dev/video*
```

Capture one test frame:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/camera_diag.py --device /dev/video0 --save /tmp/dectmo_camera_test.jpg
```

If `/dev/video0` fails, try `/dev/video1` or the device shown by `v4l2-ctl`.

## Phase 3: Browser Control With Live Video

Start the web controller with camera streaming:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/web_control.py --port /dev/ttyACM0 --wheel-mode ordinary --host 0.0.0.0 --http-port 8000 --camera-device /dev/video0
```

Open from another computer:

```text
http://192.168.0.167:8000
```

The live camera endpoint is:

```text
http://192.168.0.167:8000/camera.mjpg
```

The health endpoint is:

```text
http://192.168.0.167:8000/health
```
