from __future__ import annotations

import argparse
import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlparse

from camera_stream import CameraConfig, UsbCamera
from car import DEFAULT_BAUD, DEFAULT_DURATION_MS, DEFAULT_SPEED, Car, CarError


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DECTmo Car Control</title>
  <style>
    :root {
      color: #111;
      background: #f5f7f8;
      font-family: Arial, sans-serif;
    }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
    }
    main {
      width: min(980px, calc(100vw - 32px));
      padding: 24px 0;
    }
    h1 {
      font-size: 28px;
      margin: 0 0 16px;
    }
    .status {
      margin: 0 0 20px;
      min-height: 24px;
      font-size: 16px;
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(280px, 1fr) minmax(320px, 1.2fr);
      gap: 24px;
      align-items: start;
    }
    .video {
      width: 100%;
      aspect-ratio: 4 / 3;
      background: #111;
      border: 2px solid #141414;
      overflow: hidden;
    }
    .video img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
    .pad {
      display: grid;
      grid-template-columns: repeat(3, minmax(86px, 1fr));
      gap: 12px;
      align-items: stretch;
    }
    button {
      min-height: 84px;
      border: 2px solid #141414;
      border-radius: 8px;
      background: #fff;
      color: #111;
      font-size: 20px;
      font-weight: 700;
      cursor: pointer;
    }
    button:active,
    button.active {
      background: #18b26b;
      color: #fff;
    }
    .stop {
      background: #d72638;
      color: #fff;
    }
    .controls {
      display: flex;
      gap: 16px;
      align-items: center;
      margin-top: 20px;
      flex-wrap: wrap;
    }
    label {
      font-size: 16px;
    }
    input[type="range"] {
      width: 220px;
    }
    .hint {
      margin-top: 16px;
      font-size: 15px;
      line-height: 1.4;
    }
    @media (max-width: 780px) {
      .layout {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <main>
    <h1>DECTmo Car Control</h1>
    <p class="status" id="status">Ready</p>
    <div class="layout">
      <section aria-label="movement controls">
        <div class="pad">
          <span></span>
          <button data-action="forward">Forward</button>
          <span></span>
          <button data-action="left">Left</button>
          <button class="stop" data-action="stop">Stop</button>
          <button data-action="right">Right</button>
          <span></span>
          <button data-action="backward">Backward</button>
          <span></span>
        </div>
        <section class="controls">
          <label>Speed <span id="speedValue">50</span></label>
          <input id="speed" type="range" min="10" max="100" value="50">
        </section>
        <p class="hint">Use W, A, S, D or the arrow keys. Space stops the car.</p>
      </section>
      <section aria-label="live camera">
        <div class="video">
          <img id="cameraFeed" src="/camera.mjpg" alt="Live camera footage">
        </div>
        <p class="hint" id="cameraStatus">Camera stream loading</p>
      </section>
    </div>
  </main>
  <script>
    const statusEl = document.getElementById("status");
    const speedEl = document.getElementById("speed");
    const speedValueEl = document.getElementById("speedValue");
    const cameraStatusEl = document.getElementById("cameraStatus");
    const cameraFeedEl = document.getElementById("cameraFeed");
    let repeatTimer = null;
    let activeButton = null;

    speedEl.addEventListener("input", () => {
      speedValueEl.textContent = speedEl.value;
    });

    async function send(action) {
      const response = await fetch("/command", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          action,
          speed: Number(speedEl.value)
        })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const result = await response.json();
      statusEl.textContent = result.movement.action;
    }

    function start(action, button) {
      stopRepeat(false);
      activeButton = button;
      if (activeButton) activeButton.classList.add("active");
      send(action).catch(showError);
      if (action !== "stop") {
        repeatTimer = window.setInterval(() => send(action).catch(showError), 140);
      }
    }

    function stopRepeat(sendStop = true) {
      if (repeatTimer) {
        window.clearInterval(repeatTimer);
        repeatTimer = null;
      }
      if (activeButton) {
        activeButton.classList.remove("active");
        activeButton = null;
      }
      if (sendStop) send("stop").catch(showError);
    }

    function showError(error) {
      statusEl.textContent = error.message;
    }

    async function loadHealth() {
      try {
        const response = await fetch("/health");
        const health = await response.json();
        statusEl.textContent = `Bridge ${health.bridge}`;
        if (!health.camera.enabled) {
          cameraStatusEl.textContent = "Camera disabled";
          cameraFeedEl.removeAttribute("src");
        } else if (health.camera.last_error) {
          cameraStatusEl.textContent = health.camera.last_error;
        } else {
          cameraStatusEl.textContent = `Camera ${health.camera.device}`;
        }
      } catch (error) {
        statusEl.textContent = error.message;
      }
    }

    document.querySelectorAll("button[data-action]").forEach((button) => {
      const action = button.dataset.action;
      button.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        start(action, button);
      });
      button.addEventListener("pointerup", () => stopRepeat(action !== "stop"));
      button.addEventListener("pointerleave", () => stopRepeat(action !== "stop"));
    });

    const keys = {
      ArrowUp: "forward",
      w: "forward",
      W: "forward",
      ArrowDown: "backward",
      s: "backward",
      S: "backward",
      ArrowLeft: "left",
      a: "left",
      A: "left",
      ArrowRight: "right",
      d: "right",
      D: "right",
      " ": "stop"
    };

    window.addEventListener("keydown", (event) => {
      if (event.repeat) return;
      const action = keys[event.key];
      if (!action) return;
      event.preventDefault();
      start(action, null);
    });

    window.addEventListener("keyup", (event) => {
      if (keys[event.key]) stopRepeat(keys[event.key] !== "stop");
    });

    cameraFeedEl.addEventListener("error", () => {
      cameraStatusEl.textContent = "Camera stream unavailable";
    });

    window.addEventListener("blur", () => stopRepeat(true));
    loadHealth();
    window.setInterval(loadHealth, 5000);
  </script>
</body>
</html>
"""


class Controller:
    def __init__(self, car: Car, camera: UsbCamera, pulse_ms: int) -> None:
        self.car = car
        self.camera = camera
        self.pulse_ms = pulse_ms
        self.lock = Lock()

    def command(self, payload: dict[str, object]) -> dict[str, object]:
        action = str(payload.get("action", "stop"))
        speed = int(payload.get("speed", DEFAULT_SPEED))
        duration_ms = int(payload.get("duration_ms", payload.get("durationMs", self.pulse_ms)))
        with self.lock:
            movement = self.car.send_move(action=action, speed=speed, duration_ms=duration_ms)
        return {"ok": True, "movement": movement.to_dict()}

    def health(self) -> dict[str, object]:
        with self.lock:
            bridge_info = self.car.info()
            bridge = self.car.ping() or "no-response"
        return {
            "ok": bridge == "PONG",
            "bridge": bridge,
            "bridge_info": bridge_info,
            "serial_port": self.car.port,
            "camera": self.camera.status(),
        }


class RequestHandler(BaseHTTPRequestHandler):
    controller: Controller

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.send_html()
            return
        if path == "/health":
            self.send_json(self.controller.health())
            return
        if path == "/camera.mjpg":
            self.send_camera_stream()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def send_html(self) -> None:
        payload = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, body: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def send_camera_stream(self) -> None:
        if not self.controller.camera.enabled:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        frame_delay = 1 / max(1, self.controller.camera.config.fps)
        while True:
            frame = self.controller.camera.read_jpeg()
            if frame is None:
                time.sleep(0.25)
                continue
            try:
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(frame)}\r\n\r\n".encode("ascii"))
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            time.sleep(frame_delay)

    def do_POST(self) -> None:
        if self.path != "/command":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            result = self.controller.command(payload)
        except (ValueError, json.JSONDecodeError, CarError) as exc:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.end_headers()
            self.wfile.write(str(exc).encode("utf-8"))
            return
        self.send_json(result, HTTPStatus.OK)

    def log_message(self, format: str, *args) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Browser controller for the Pico car.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--port", help="Serial port, for example /dev/ttyACM0.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="Pico serial baud rate.")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP bind host.")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP server port.")
    parser.add_argument("--pulse-ms", type=int, default=DEFAULT_DURATION_MS, help="Movement pulse duration.")
    parser.add_argument("--camera-device", default="/dev/video0", help="USB camera device.")
    parser.add_argument("--camera-width", type=int, default=640, help="Camera capture width.")
    parser.add_argument("--camera-height", type=int, default=480, help="Camera capture height.")
    parser.add_argument("--camera-fps", type=int, default=15, help="Camera stream FPS.")
    parser.add_argument("--camera-quality", type=int, default=80, help="JPEG quality.")
    parser.add_argument("--no-camera", action="store_true", help="Disable camera streaming.")
    parser.add_argument(
        "--wheel-mode",
        choices=("ordinary", "mecanum"),
        default="ordinary",
        help="ordinary turns left/right; mecanum strafes left/right.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with Car(args.port, args.baud, wheel_mode=args.wheel_mode) as car:
            camera_device = "none" if args.no_camera else args.camera_device
            camera = UsbCamera(
                CameraConfig(
                    device=camera_device,
                    width=args.camera_width,
                    height=args.camera_height,
                    fps=args.camera_fps,
                    quality=args.camera_quality,
                )
            )
            RequestHandler.controller = Controller(car, camera, args.pulse_ms)
            server = ThreadingHTTPServer((args.host, args.http_port), RequestHandler)
            print(f"Serial port: {car.port}")
            print(f"Open http://{args.host}:{args.http_port}")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                camera.close()
                server.server_close()
    except CarError as exc:
        print(f"Web controller error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
