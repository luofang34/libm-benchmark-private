import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from ingest_h743 import accept

CAPTURE = Path(__file__).resolve().parents[1] / 'results/raw-logs/stm32h743'


class HardwareAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.capture = Path(self.temp.name)
        for name in ['device.json', 'payload.bin']:
            shutil.copyfile(CAPTURE / name, self.capture / name)

    def change_identity(self, **changes):
        path = self.capture / 'device.json'
        device = json.loads(path.read_text()) | changes
        path.write_text(json.dumps(device))

    def test_real_capture_passes_mpfr_and_image_validation(self):
        accept(self.capture, CAPTURE / 'firmware')
        self.assertTrue((self.capture / 'accuracy.csv').exists())

    def test_substituted_firmware_is_rejected(self):
        self.change_identity(firmware_sha='0' * 64)
        with self.assertRaisesRegex(ValueError, 'running firmware differs'):
            accept(self.capture, CAPTURE / 'firmware')

    def test_flush_to_zero_is_rejected(self):
        self.change_identity(fpscr=1 << 24)
        with self.assertRaisesRegex(ValueError, 'IEEE rounding/subnormal mode'):
            accept(self.capture, CAPTURE / 'firmware')

    def test_truncated_timing_with_valid_transport_hash_is_rejected(self):
        path = self.capture / 'payload.bin'
        lines = path.read_bytes().splitlines(keepends=True)
        payload = b''.join(lines[:2] + lines[3:])
        path.write_bytes(payload)
        self.change_identity(payload_sha256=hashlib.sha256(payload).hexdigest())
        with self.assertRaisesRegex(ValueError, 'timing stream is incomplete'):
            accept(self.capture, CAPTURE / 'firmware')


if __name__ == '__main__':
    unittest.main()
