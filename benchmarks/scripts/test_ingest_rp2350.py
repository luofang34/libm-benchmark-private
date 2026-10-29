import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from ingest_rp2350 import accept

ROOT = Path(__file__).resolve().parents[1] / 'results/raw-logs'


class RP2350Acceptance(unittest.TestCase):
    def capture(self, mode):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        capture = Path(temporary.name)
        source = ROOT / ('rp2350-' + mode)
        for name in ['device.json', 'payload.bin']:
            shutil.copyfile(source / name, capture / name)
        return capture, source / 'firmware'

    def test_real_arm_and_hazard3_captures_pass(self):
        for mode in ['arm', 'riscv']:
            with self.subTest(mode=mode):
                capture, firmware = self.capture(mode)
                device, manifest = accept(capture, firmware)
                self.assertEqual(device['mode'], manifest['mode'])
                self.assertTrue((capture / 'accuracy.csv').exists())

    def test_real_dcp_failure_cannot_be_accepted(self):
        capture, firmware = self.capture('dcp')
        with self.assertRaises(subprocess.CalledProcessError):
            accept(capture, firmware)

    def test_dcp_failed_evidence_can_be_retained_without_losing_mpfr_results(self):
        capture, firmware = self.capture('dcp')
        accept(capture, firmware, record_accuracy_failure=True)
        self.assertIn('8925239461535591', (capture / 'accuracy.csv').read_text())

    def test_dcp_access_cannot_enter_software_population(self):
        capture, firmware = self.capture('arm')
        path = capture / 'device.json'
        device = json.loads(path.read_text())
        device['cpacr'] |= 3 << 8
        path.write_text(json.dumps(device))
        with self.assertRaisesRegex(ValueError, 'DCP access'):
            accept(capture, firmware, record_accuracy_failure=True)

    def test_clock_crosscheck_rejects_invalid_cycle_conversion(self):
        capture, firmware = self.capture('riscv')
        path = capture / 'device.json'
        path.write_text(json.dumps(json.loads(path.read_text()) | {'sof_clock_hz': 48_000_000}))
        with self.assertRaisesRegex(ValueError, 'USB frame clock'):
            accept(capture, firmware)

    def test_hardware_fp_cannot_enter_hazard3_population(self):
        capture, firmware = self.capture('riscv')
        path = capture / 'device.json'
        device = json.loads(path.read_text())
        device['misa'] |= 1 << 3
        path.write_text(json.dumps(device))
        with self.assertRaisesRegex(ValueError, 'Hazard3'):
            accept(capture, firmware)


if __name__ == '__main__':
    unittest.main()
