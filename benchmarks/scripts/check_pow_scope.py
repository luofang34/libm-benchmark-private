"""Compile real libm objects and enforce which targets contain the pow lookup tables."""
import argparse
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    'wasm32-unknown-unknown': True,
    'aarch64-apple-darwin': True,
    'aarch64-unknown-linux-gnu': True,
    'x86_64-unknown-linux-gnu': True,
    'x86_64-pc-windows-msvc': True,
    'wasm32-wasip1': False,
    'aarch64-unknown-none': False,
    'thumbv7em-none-eabihf': False,
    'riscv32imac-unknown-none-elf': False,
    'aarch64-apple-ios': False,
    'x86_64-apple-darwin': False,
}


def tables():
    source = (ROOT / 'libm/src/math/pow/table.rs').read_text()
    arrays = {name: ast.literal_eval(value) for name, value in
              re.findall(r'pub\(super\) const (\w+):.*? = (.*?);', source, re.S)}
    return {name: b''.join(struct.pack('<Q', word) for row in arrays[name] for word in row)
            for name in ['LOG_TAB', 'EXP_TAB']}


def check(directory):
    expected_tables = tables()
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for target, selected in TARGETS.items():
        destination = directory / target
        destination.mkdir(exist_ok=True)
        command = ['cargo', 'rustc', '--manifest-path', str(ROOT / 'libm/Cargo.toml'), '--locked',
                   '--lib', '--release', '--no-default-features', '--target', target,
                   '--', '--emit=obj,llvm-ir']
        env = os.environ | {'CARGO_TARGET_DIR': str(directory / 'target'), 'RUSTFLAGS': ''}
        with (destination / 'build.log').open('w') as stream:
            subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, check=True)
        artifacts = list((directory / 'target' / target / 'release').rglob('libm-*.o'))
        if len(artifacts) != 1:
            raise ValueError(f'{target}: expected one libm object, found {len(artifacts)}')
        artifact = artifacts[0]
        obj = artifact.read_bytes()
        counts = {name: obj.count(data) for name, data in expected_tables.items()}
        if any(count != int(selected) for count in counts.values()):
            raise ValueError(f'{target}: unexpected pow table selection: {counts}')
        (destination / 'libm.o.gz').write_bytes(gzip.compress(obj, mtime=0))
        cfg = subprocess.check_output(['rustc', '--print', 'cfg', '--target', target], text=True)
        record = dict(target_triple=target, candidate_selected=selected, table_occurrences=counts,
                      object_sha256=hashlib.sha256(obj).hexdigest(), object_bytes=len(obj),
                      target_cfg=cfg.splitlines(), command=command, status='PASS')
        records.append(record)
        (directory / 'scope.json').write_text(json.dumps(records, indent=2) + '\n')
        print(target, 'candidate' if selected else 'fallback', 'PASS', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    check(parser.parse_args().output.resolve())
