from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

from serial_car import DEFAULT_BAUD, DEFAULT_PULSE_MS, SerialCar, SerialCarError


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
      width: min(680px, calc(100vw - 32px));
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
    select {
      font-size: 16px;
      padding: 8px;
      border-radius: 8px;
      border: 1px solid #555;
      background: white;
    }
  </style>
</head>
<body>
  <main>
    <h1>DECTmo Car Control</h1>
    <p class="status" id="status">Ready</p>
    <section class="pad" aria-label="movement controls">
      <span></span>
      <button data-action="forward">Forward</button>
      <span></span>
      <button data-action="left">Left</button>
      <button class="stop" data-action="stop">Stop</button>
      <button data-action="right">Right</button>
      <span></span>
      <button data-action="backward">Backward</button>
      <span></span>
    </section>
    <section class="controls">
      <label>Speed <span id="speedValue">50</span></label>
      <input id="speed" type="range" min="10" max="100" value="50">
      <label>
        Wheel mode
        <select id="wheelMode">
          <option value="ordinary">ordinary</option>
          <option value="mecanum">mecanum</option>
        </select>
      </label>
    </section>
  </main>
  <script>
    const statusEl = document.getElementById("status");
    const speedEl = document.getElementById("speed");
    const speedValueEl = document.getElementById("speedValue");
    const wheelModeEl = document.getElementById("wheelMode");
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
          speed: Number(speedEl.value),
          wheelMode: wheelModeEl.value
        })
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      statusEl.textContent = action;
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
  </script>
</body>
</html>
"""


class Controller:
    def __init__(self, car: SerialCar, default_wheel_mode: str, pulse_ms: int) -> None:
        self.car = car
        self.default_wheel_mode = default_wheel_mode
        self.pulse_ms = pulse_ms
        self.lock = Lock()

    def command(self, action: str, speed: int, wheel_mode: str | None = None) -> None:
        mode = wheel_mode or self.default_wheel_mode
        if mode not in {"ordinary", "mecanum"}:
            raise SerialCarError("wheelMode must be ordinary or mecanum.")
        with self.lock:
            self.car.send_move(action, speed, self.pulse_ms, mode)


class RequestHandler(BaseHTTPRequestHandler):
    controller: Controller

    def do_GET(self) -> None:
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        payload = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:
        if self.path != "/command":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            action = str(payload.get("action", "stop"))
            speed = int(payload.get("speed", 50))
            wheel_mode = str(payload.get("wheelMode", ""))
            self.controller.command(action, speed, wheel_mode or None)
        except (ValueError, json.JSONDecodeError, SerialCarError) as exc:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.end_headers()
            self.wfile.write(str(exc).encode("utf-8"))
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def log_message(self, format: str, *args) -> None:
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Browser controller for the Pico car.")
    parser.add_argument("--port", help="Serial port, for example /dev/ttyACM0.")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=8000)
    parser.add_argument("--pulse-ms", type=int, default=DEFAULT_PULSE_MS)
    parser.add_argument(
        "--wheel-mode",
        choices=("ordinary", "mecanum"),
        default="ordinary",
        help="Default wheel mode.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        with SerialCar(args.port, args.baud) as car:
            RequestHandler.controller = Controller(car, args.wheel_mode, args.pulse_ms)
            server = ThreadingHTTPServer((args.host, args.http_port), RequestHandler)
            print(f"Serial port: {car.port}")
            print(f"Open http://{args.host}:{args.http_port}")
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
    except SerialCarError as exc:
        print(f"Web controller error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
