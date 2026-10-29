"""Retrieve a retained result frame over a detected POSIX USB CDC interface."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import termios
import time
import tty

from detect import snapshot

MAX_FRAME_BYTES = 32 * 1024 * 1024


def read_line(fd, selector, pending, deadline):
    while b'\n' not in pending:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not selector.select(remaining):
            raise TimeoutError('firmware did not provide a complete response')
        block = os.read(fd, 4096)
        if not block:
            raise EOFError('device disconnected before transfer completed')
        pending.extend(block)
        if len(pending) > MAX_FRAME_BYTES:
            raise ValueError('telemetry frame exceeds the size limit')
    line, _, rest = pending.partition(b'\n')
    pending[:] = rest
    return bytes(line).rstrip(b'\r')


def retrieve(fd, directory, timeout=30):
    pending = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(fd, selectors.EVENT_READ)
        deadline = time.monotonic() + timeout
        os.write(fd, b'POWBENCH/1 INFO\n')
        metadata = json.loads(read_line(fd, selector, pending, deadline))
        if metadata.get('protocol') != 'POWBENCH/1' or metadata.get('state') != 'complete':
            raise ValueError('device has not identified a completed pow benchmark')
        for key in ['run_id', 'firmware_sha', 'dataset_sha', 'payload_sha256']:
            if not metadata.get(key):
                raise ValueError(f'missing firmware identity: {key}')
        os.write(fd, b'POWBENCH/1 RESULTS\n')
        header = read_line(fd, selector, pending, deadline).decode().split()
        if len(header) != 2 or header[0] != 'BYTES':
            raise ValueError('missing exact payload length')
        size = int(header[1])
        if not 0 < size <= MAX_FRAME_BYTES:
            raise ValueError('invalid payload length')
        while len(pending) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError('result transfer timed out')
            chunk = os.read(fd, min(65536, size - len(pending)))
            if not chunk:
                raise EOFError('incomplete result transfer')
            pending.extend(chunk)
        payload = bytes(pending[:size])
        if hashlib.sha256(payload).hexdigest() != metadata['payload_sha256']:
            raise ValueError('telemetry checksum mismatch')
        directory.mkdir(parents=True, exist_ok=False)
        (directory / 'device.json').write_text(json.dumps(metadata, indent=2) + '\n')
        (directory / 'payload.bin').write_bytes(payload)
        return metadata


def collect(port, directory):
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attributes = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        # USB CDC baud is a line-coding hint; no DTR/RTS toggle is used for reset.
        return retrieve(fd, directory)
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, attributes)
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inventory = snapshot()
    ports = inventory['serial_ports']
    if not ports:
        print(json.dumps(inventory | {'measurement_status': 'BLOCKED', 'reason': 'No USB CDC device detected.'}))
        return
    for i, port in enumerate(ports):
        try:
            result = collect(port, args.output / f'capture-{i}')
            print(json.dumps({'port': port, 'run_id': result['run_id'], 'capture_status': 'PASS'}))
        except (OSError, ValueError, TimeoutError) as error:
            print(json.dumps({'port': port, 'capture_status': 'BLOCKED', 'reason': str(error)}))


if __name__ == '__main__':
    main()
