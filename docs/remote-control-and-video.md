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
