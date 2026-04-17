from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "control" / "pi5_controller"))

from nrf_modem import AtCommandResult, NrfModemProbe, clean_response_lines, parse_firmware_version


class NrfModemTest(unittest.TestCase):
    def test_clean_response_lines_handles_crlf_bytes(self) -> None:
        self.assertEqual(
            clean_response_lines(b"\r\nmfw_nrf91x1_2.0.2\r\n\r\nOK\r\n"),
            ("mfw_nrf91x1_2.0.2", "OK"),
        )

    def test_parse_firmware_version_ignores_ok(self) -> None:
        self.assertEqual(
            parse_firmware_version(("mfw_nrf91x1_2.0.2", "OK")),
            "mfw_nrf91x1_2.0.2",
        )

    def test_probe_identifies_modem_port(self) -> None:
        probe = NrfModemProbe(
            port="/dev/ttyACM1",
            at=AtCommandResult(command="AT", lines=("OK",)),
            firmware=AtCommandResult(
                command="AT+CGMR",
                lines=("mfw_nrf91x1_2.0.2", "OK"),
            ),
        )

        self.assertTrue(probe.responds_to_at)
        self.assertTrue(probe.is_modem_port)
        self.assertEqual(probe.firmware_version, "mfw_nrf91x1_2.0.2")


if __name__ == "__main__":
    unittest.main()
