import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from ingest_rp2040 import accept, capability

ROOT = Path(__file__).resolve().parents[1] / 'results/raw-logs/rp2040'


class RP2040Acceptance(unittest.TestCase):
    def capture(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        capture = Path(temporary.name)
        for name in ['device.json', 'payload.bin']:
            shutil.copyfile(ROOT / name, capture / name)
        return capture, ROOT / 'firmware'

    def alter_identity(self, capture, **fields):
        path = capture / 'device.json'
        path.write_text(json.dumps(json.loads(path.read_text()) | fields))

    def test_real_capture_passes_mpfr_and_cycle_crosscheck(self):
        capture, firmware = self.capture()
        device, manifest = accept(capture, firmware)
        self.assertEqual(device['firmware_sha'], manifest['firmware_sha'])
        self.assertIn('0.4999999999955404', (capture / 'accuracy.csv').read_text())

    def test_captured_divider_two_configuration_is_rejected(self):
        device = json.loads((ROOT / 'rejected-spi-div2/device.json').read_text())
        manifest = json.loads((ROOT / 'firmware/manifest.json').read_text())
        with self.assertRaisesRegex(ValueError, 'Flash configuration'):
            capability(device, manifest)

    def test_external_systick_clock_is_rejected(self):
        capture, firmware = self.capture()
        device = json.loads((capture / 'device.json').read_text())
        self.alter_identity(capture, systick_csr=device['systick_csr'] & ~4)
        with self.assertRaisesRegex(ValueError, 'processor clock'):
            accept(capture, firmware)

    def test_usb_clock_disagreement_is_rejected(self):
        capture, firmware = self.capture()
        self.alter_identity(capture, sof_clock_hz=1_000_000)
        with self.assertRaisesRegex(ValueError, 'USB frame clock'):
            accept(capture, firmware)

    def test_complete_payload_with_wrong_batch_interval_is_rejected(self):
        capture, firmware = self.capture()
        path = capture / 'payload.bin'
        lines = path.read_bytes().splitlines(keepends=True)
        fields = lines[1].decode().strip().split(',')
        row = lines[2].decode().strip().split(',')
        row[fields.index('batch_us')] = '1'
        lines[2] = (','.join(row) + '\n').encode()
        payload = b''.join(lines)
        path.write_bytes(payload)
        self.alter_identity(capture, payload_sha256=hashlib.sha256(payload).hexdigest())
        with self.assertRaisesRegex(ValueError, 'independent timer'):
            accept(capture, firmware)

    def test_different_firmware_cannot_be_accepted(self):
        capture, firmware = self.capture()
        self.alter_identity(capture, firmware_sha='0' * 64)
        with self.assertRaisesRegex(ValueError, 'running firmware'):
            accept(capture, firmware)


if __name__ == '__main__':
    unittest.main()
