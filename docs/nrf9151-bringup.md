# nRF9151 Bring-Up

This phase verifies that the Raspberry Pi 5 can see and talk to the nRF9151 board over USB before any DECT NR+ movement or video work.

## Current Verified Result

The Pi sees the nRF9151 board through the SEGGER J-Link USB interface:

```text
ID 1366:1069 SEGGER J-Link
```

The useful AT modem/application port is:

```text
/dev/ttyACM1
```

Verified safe commands:

```text
AT       -> OK
AT+CGMR  -> mfw_nrf91x1_2.0.2
```

`/dev/ttyACM2` currently does not reply to these AT commands, so do not use it as the Pi-side modem command port unless the board firmware changes.

## Repeatable Diagnosis

Run this on the Pi:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/diagnose_nrf_modem.py
```

Or probe explicit ports:

```bash
python3 control/pi5_controller/diagnose_nrf_modem.py --port /dev/ttyACM1 --port /dev/ttyACM2
```

Expected useful result:

```text
=== /dev/ttyACM1 ===
> AT
OK
> AT+CGMR
mfw_nrf91x1_2.0.2
OK
Result: OK modem AT port, firmware=mfw_nrf91x1_2.0.2
```

This only proves USB serial and modem AT connectivity. It does not prove DECT NR+ packet transport.

## Meaning For DECTmo

The next implementation target is a Pi-side nRF adapter that uses `/dev/ttyACM1` as the board command port once the nRF9151 firmware exposes the required DECT NR+ send/receive behavior.

The safe order remains:

1. Heartbeat packet.
2. Emergency stop packet.
3. One short low-speed movement command with the car lifted.
4. Video packetization only after command reliability is measured.

## Open Firmware Question

The board currently responds as an nRF91x1 modem AT endpoint. Before real DECT NR+ transport can be tested, both nRF9151 boards need compatible firmware that can exchange application payloads over DECT NR+ and expose those payloads to the host.

Do not treat AT modem connectivity as proof that our DECTmo packets are crossing the radio link.
