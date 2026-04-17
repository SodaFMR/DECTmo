# nRF9151 Firmware Flashing

This note covers the downloaded Nordic bundle:

```text
nrf9151dk_mfw-2.0.4_sdk-3.2.1/
```

That folder is intentionally ignored by Git. Keep it local, and do not commit Nordic firmware bundles into the repository.

## What The Bundle Contains

The included `CONTENTS.txt` says this bundle was built with nRF Connect SDK `v3.2.1` and contains:

```text
mfw_nrf91x1_2.0.4.zip
img_app_bl/nrf9151dk_at_client_2026-02-24_d8887f6f.hex
img_app_bl/nrf9151dk_modem_shell_2026-02-24_d8887f6f.hex
img_app_bl/nrf9151dk_serial_modem_v1.0.0.hex
img_app_bl/nrf9151dk_asset_tracker_template_v1.2.9.hex
```

For DECTmo bring-up, the safest first target is:

```text
mfw_nrf91x1_2.0.4.zip
img_app_bl/nrf9151dk_at_client_2026-02-24_d8887f6f.hex
```

The AT Client keeps the board usable through AT commands, which matches the current verified `/dev/ttyACM1` behavior.

## Important Limitation

Updating this package does not, by itself, prove DECT NR+ payload transport. It updates the modem firmware and application image on the board. The current DECTmo radio test still needs firmware on both nRF9151 boards that can send and receive application payload bytes over DECT NR+.

Nordic's public nRF9151 DK page notes that official DECT NR+ firmware binaries are obtained through Nordic sales/support. Treat this bundle as the standard modem/application update unless the selected image explicitly exposes the DECT NR+ payload behavior we need.

## Recommended GUI Flashing Path

Use this path first because it is the least ambiguous way to update both modem firmware and application firmware.

1. Install or open **nRF Connect for Desktop**.
2. Install/open the **Programmer** app.
3. Connect the nRF9151 DK through its J-Link USB port.
4. Select the J-Link device. In our current setup the serial number is:

```text
001051202270
```

5. Update the modem firmware:

```text
nrf9151dk_mfw-2.0.4_sdk-3.2.1/mfw_nrf91x1_2.0.4.zip
```

Use the Programmer application's modem update flow for the `.zip` file.

6. Program the application image:

```text
nrf9151dk_mfw-2.0.4_sdk-3.2.1/img_app_bl/nrf9151dk_at_client_2026-02-24_d8887f6f.hex
```

Use the full application image from `img_app_bl/`, not one of the FOTA-only folders.

7. Reset the board after flashing.

## Optional CLI Application Flash

If Nordic command-line tools are installed, the application `.hex` can be programmed through J-Link with `nrfjprog`:

```bash
nrfjprog --ids
nrfjprog -f nrf91 --snr 001051202270 \
  --program nrf9151dk_mfw-2.0.4_sdk-3.2.1/img_app_bl/nrf9151dk_at_client_2026-02-24_d8887f6f.hex \
  --sectorerase --verify --reset
```

Use nRF Connect Programmer for the modem firmware `.zip` unless a known-good Nordic CLI modem-update flow is available on the flashing machine.

## Verify After Flashing

Reconnect the board to the Pi 5 and run:

```bash
cd ~/Desktop/DECTmo
python3 control/pi5_controller/diagnose_nrf_modem.py
```

Expected result after modem update:

```text
=== /dev/ttyACM1 ===
> AT
OK
> AT+CGMR
mfw_nrf91x1_2.0.4
OK
Result: OK modem AT port, firmware=mfw_nrf91x1_2.0.4
```

If `/dev/ttyACM1` changes after flashing, run:

```bash
python3 -m serial.tools.list_ports -v
python3 control/pi5_controller/diagnose_nrf_modem.py
```

The diagnostic scans SEGGER J-Link CDC ports and will identify the AT-responsive port.

## If Flashing From The Pi 5

Because the firmware folder is ignored by Git, `git pull` will not copy it to the Pi. Download the Nordic bundle on the Pi or copy the local folder manually, for example:

```bash
scp -r nrf9151dk_mfw-2.0.4_sdk-3.2.1 qartia@192.168.0.167:~/Desktop/DECTmo/
```

Then use the same file paths from this document on the Pi.
