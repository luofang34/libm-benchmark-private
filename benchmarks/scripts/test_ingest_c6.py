import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from build_c6 import app_image, audit
from ingest_c6 import accept

ROOT = Path(__file__).resolve().parents[1] / 'results/raw-logs/esp32c6'


class C6Acceptance(unittest.TestCase):
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

    def test_real_capture_passes_mpfr_and_clock_crosscheck(self):
        capture, firmware = self.capture()
        device, manifest = accept(capture, firmware)
        self.assertEqual(device['firmware_sha'], manifest['firmware_sha'])
        self.assertIn('0.4999999999955404', (capture / 'accuracy.csv').read_text())

    def test_saturating_or_noncycle_counter_is_rejected(self):
        for fields in [dict(counter_mode=3), dict(counter_event=2), dict(mstatus=9)]:
            with self.subTest(fields=fields):
                capture, firmware = self.capture()
                self.alter_identity(capture, **fields)
                with self.assertRaisesRegex(ValueError, 'counter must count cycles'):
                    accept(capture, firmware)

    def test_clock_ratio_and_memory_configuration_are_enforced(self):
        for fields, message in [(dict(timer_clock_hz=80_000_000), 'independent timer'),
                                (dict(mspi_clock=0xb00), 'MSPI clock'),
                                (dict(spi_clock=0x10001), 'MSPI clock'),
                                (dict(cache_ctrl=1), 'cache configuration')]:
            with self.subTest(fields=fields):
                capture, firmware = self.capture()
                self.alter_identity(capture, **fields)
                with self.assertRaisesRegex(ValueError, message):
                    accept(capture, firmware)

    def test_complete_payload_with_wrong_batch_interval_is_rejected(self):
        capture, firmware = self.capture()
        path = capture / 'payload.bin'
        lines = path.read_bytes().splitlines(keepends=True)
        columns = lines[1].decode().strip().split(',')
        row = lines[2].decode().strip().split(',')
        row[columns.index('batch_us')] = '1'
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

    def test_real_merged_image_extent_and_integrity(self):
        merged = (ROOT / 'firmware/merged.bin').read_bytes()
        image, segments = app_image(merged)
        self.assertEqual(image, (ROOT / 'firmware/pow-esp32c6.bin').read_bytes())
        self.assertEqual(len(segments), 4)
        damaged = bytearray(merged)
        damaged[0x10020] ^= 1
        for corrupt in [bytes(damaged), merged[:-1], merged[:0x10010]]:
            with self.subTest(length=len(corrupt)), self.assertRaises(ValueError):
                app_image(corrupt)

    def test_linked_arithmetic_calls_match_rom_runtime(self):
        reports = {name: (ROOT / 'firmware' / (name + '.txt')).read_text()
                   for name in ['assembly', 'symbols']}
        helpers = audit(reports, None)
        self.assertGreater(helpers['__muldf3']['calls'], 0)
        self.assertEqual(helpers['__muldf3']['address'], '0x40000a64')
        with self.assertRaisesRegex(ValueError, 'ROM floating-point call missing'):
            audit(reports | {'symbols': reports['symbols'].replace('__muldf3', 'other_mul')}, None)


if __name__ == '__main__':
    unittest.main()
