import json
from pathlib import Path
import shutil
import tempfile
import unittest

from ingest_f411 import accept

CAPTURE = Path(__file__).resolve().parents[1] / 'results/raw-logs/stm32f411'


class F411Acceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.capture = Path(self.temp.name)
        for name in ['device.json', 'payload.bin']:
            shutil.copyfile(CAPTURE / name, self.capture / name)

    def change_identity(self, **changes):
        path = self.capture / 'device.json'
        path.write_text(json.dumps(json.loads(path.read_text()) | changes))

    def test_real_capture_passes_mpfr_and_image_validation(self):
        accept(self.capture, CAPTURE / 'firmware')
        self.assertTrue((self.capture / 'accuracy.csv').exists())

    def test_hardware_fp64_identity_cannot_enter_software_fp64_population(self):
        self.change_identity(mvfr0=0x10110221)
        with self.assertRaisesRegex(ValueError, 'capability or IEEE mode'):
            accept(self.capture, CAPTURE / 'firmware')

    def test_inconsistent_clock_is_rejected(self):
        self.change_identity(clock_hz=96_000_000)
        with self.assertRaisesRegex(ValueError, 'timer frequency differs'):
            accept(self.capture, CAPTURE / 'firmware')

    def test_ambiguous_crystal_measurement_is_rejected(self):
        self.change_identity(hse_estimate_hz=24_000_000)
        with self.assertRaisesRegex(ValueError, 'ambiguous HSE measurement'):
            accept(self.capture, CAPTURE / 'firmware')


if __name__ == '__main__':
    unittest.main()
