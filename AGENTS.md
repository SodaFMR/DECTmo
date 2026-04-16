# DECTmo Project Notes

These notes capture the working assumptions for future development sessions.

## Operating Rules

- Commit and push every intentional repo change before ending a work iteration.
- Use Conventional Commit prefixes, for example `feat:`, `fix:`, `docs:`, `test:`, or `chore:`.
- Keep the Freenove vendor package local and ignored. Do not commit `Freenove_4WD_Car_Kit_for_Raspberry_Pi_Pico-main/`.
- The Raspberry Pi 5 project path currently used during bring-up is `~/Desktop/DECTmo`.
- Favor small, testable iterations. Each hardware-facing change needs a no-motor or low-risk test before full movement tests.

## Hardware Roles

- Raspberry Pi 5 is the main controller and network host.
- Raspberry Pi Pico receives serial commands over USB and directly drives the Freenove motor pins.
- The Pico currently runs `control/pico_micropython_bridge/main.py` as `main.py`.
- USB from Pi 5 to Pico is enough for serial and Pico power. The Freenove battery pack is required for motor movement.

## Control Contract

The Pi sends newline-terminated commands to the Pico:

```text
PING          firmware health check
S             stop
F 50 250      forward at speed 50 for 250 ms
B 50 250      backward at speed 50 for 250 ms
L 50 250      ordinary-wheel left turn
R 50 250      ordinary-wheel right turn
DRIVE 50 -50  raw left/right differential speeds
```

The expected bridge replies are:

```text
READY micropython_serial_bridge
INFO bridge=micropython_serial_bridge version=1.1.0 motor_direction=-1
PONG
OK STOP
OK MOVE
OK AUTO_STOP
```

## Product Direction

- Same-WiFi control should work from another computer, including idFelipe, through a browser hosted by the Pi 5.
- Movement controls should support game-style `W`, `A`, `S`, `D` keys and clear front/back/left/right actions.
- USB camera video should be exposed from the Pi 5 as live footage in the same browser control surface.
- Code should stay simple and readable: small modules, direct names, comments only where they clarify non-obvious hardware behavior.
