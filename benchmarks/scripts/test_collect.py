import hashlib
import json
import os
from pathlib import Path
import pty
import select
import tempfile
import threading
import tty
import unittest

from collect import retrieve


class Transport(unittest.TestCase):
    def transfer(self, corrupt=False, boot_output=False):
        master, slave = pty.openpty()
        tty.setraw(slave)
        payload = b'actual serial payload\nwith a second line\n'
        failures = []

        def device():
            try:
                for expected in [b'POWBENCH/1 INFO\n', b'POWBENCH/1 RESULTS\n']:
                    received = bytearray()
                    while b'\n' not in received:
                        if not select.select([master], [], [], 3)[0]:
                            raise TimeoutError('test device did not receive request')
                        received.extend(os.read(master, 1024))
                    self.assertEqual(received, expected)
                    if expected.endswith(b'INFO\n'):
                        if boot_output:
                            os.write(master, b'ESP-ROM boot\n\x1b[0;32mI (20) boot: app\x1b[0m\npartial boot line')
                        info = dict(protocol='POWBENCH/1', state='complete', run_id='pty-test',
                                    firmware_sha='test-firmware', dataset_sha='test-dataset',
                                    payload_sha256=hashlib.sha256(payload).hexdigest())
                        os.write(master, json.dumps(info).encode() + b'\n')
                    else:
                        os.write(master, f'BYTES {len(payload)}\n'.encode())
                        os.write(master, payload if not corrupt else b'X' + payload[1:])
            except Exception as error:
                failures.append(error)

        thread = threading.Thread(target=device, name='pow-cdc-test-device')
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / 'capture'
                if corrupt:
                    with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                        retrieve(slave, destination, timeout=3)
                    self.assertFalse(destination.exists())
                else:
                    retrieve(slave, destination, timeout=3)
                    self.assertEqual((destination / 'payload.bin').read_bytes(), payload)
                    if boot_output:
                        self.assertIn(b'ESP-ROM boot', (destination / 'boot-output.bin').read_bytes())
        finally:
            thread.join(timeout=5)
            os.close(master)
            os.close(slave)
        self.assertFalse(thread.is_alive())
        if failures:
            raise failures[0]

    def test_request_response_on_real_pty(self):
        self.transfer()

    def test_corrupt_transfer_is_not_persisted(self):
        self.transfer(corrupt=True)

    def test_boot_output_preceding_real_protocol_is_preserved(self):
        self.transfer(boot_output=True)


if __name__ == '__main__':
    unittest.main()
