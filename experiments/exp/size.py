"""Measure paired application deltas and verify one shared table in linked WASM."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
from validate import execute, ROOT


def table_bytes():
    source = (ROOT / 'overlay/libm/src/math/exp_shared/table.rs').read_text().split('static EXP_TAB:', 1)[1]
    words = [int(word, 16) for word in re.findall(r'0x[0-9a-f]+', source)]
    if len(words) != 256:
        raise ValueError('unexpected shared table shape')
    return struct.pack('<256Q', *words)


def measure(work, output):
    raw, artifacts = output / 'raw', output / 'artifacts'
    table = table_bytes()
    table_path = artifacts / 'EXP_TAB.bin'
    table_path.write_bytes(table)
    sizes, table_records = [], []
    for variant in ['base', 'candidate']:
        directory = work / variant
        fixture = directory / 'fixtures'
        shutil.copytree(ROOT / 'fixtures', fixture,
                        ignore=shutil.ignore_patterns('target'), dirs_exist_ok=True)
        manifest = fixture / 'Cargo.toml'
        manifest.write_text(manifest.read_text().replace('path = "../../../libm"', 'path = "../libm"'))
        env = os.environ | {'CARGO_TARGET_DIR': str(directory / 'fixture-target'), 'RUSTFLAGS': ''}
        execute(['cargo', 'fmt', '--manifest-path', manifest, '--check'], f'fixture-fmt-{variant}', raw)
        execute(['cargo', 'clippy', '--manifest-path', manifest, '--all-targets', '--all-features',
                 '--offline', '--', '-Dwarnings'], f'fixture-clippy-{variant}', raw, env=env)
        execute(['cargo', 'doc', '--manifest-path', manifest, '--no-deps', '--all-features', '--offline'],
                f'fixture-doc-{variant}', raw, env=env | {'RUSTDOCFLAGS': '-D missing_docs -D broken_intra_doc_links'})
        for scale, features in [('minimal-exp', 'exp'), ('minimal-exp2', 'exp2'),
                                 ('medium', 'medium'), ('application', 'application')]:
            execute(['cargo', 'build', '--manifest-path', manifest, '--release', '--lib', '--offline',
                     '--target', 'wasm32-unknown-unknown', '--features', features],
                    f'size-{variant}-{scale}', raw, env=env)
            wasm = artifacts / f'{scale}-{variant}.wasm'
            wasm.write_bytes((directory / 'fixture-target/wasm32-unknown-unknown/release/exp_fixture.wasm').read_bytes())
            for optimization in ['none', 'O3', 'Oz']:
                optimized = wasm if optimization == 'none' else artifacts / f'{scale}-{variant}-{optimization}.wasm'
                if optimization != 'none':
                    execute(['wasm-opt', '--all-features', f'-{optimization}', wasm, '-o', optimized],
                            f'wasm-opt-{variant}-{scale}-{optimization}', raw)
                data = optimized.read_bytes()
                inspection = json.loads(subprocess.check_output(
                    ['node', str(ROOT / 'inspect_module.mjs'), str(optimized), str(table_path)], text=True))
                count = inspection['table_occurrences']
                if variant == 'candidate' and count != 1:
                    raise ValueError(f'{optimized}: expected one shared EXP_TAB, found {count}')
                table_records.append(dict(variant=variant, fixture=scale, optimization=optimization,
                    encoded_full_table_occurrences=data.count(table), initialized_memory=inspection,
                    module_sha256=hashlib.sha256(data).hexdigest()))
                encodings = dict(raw=data, gzip=subprocess.check_output(['gzip', '-9', '-n', '-c'], input=data),
                                 brotli=subprocess.check_output(['brotli', '-q', '11', '-c'], input=data))
                for encoding, compressed in encodings.items():
                    sizes.append(dict(fixture=scale, variant=variant, optimization=optimization,
                                      encoding=encoding, bytes=len(compressed)))
            execute(['node', ROOT / 'verify_fixture.mjs', wasm, scale],
                    f'fixture-execution-{variant}-{scale}', raw)
        shutil.copyfile(fixture / 'Cargo.lock', raw / f'fixture-{variant}-Cargo.lock')
    for row in sizes:
        baseline = next(entry['bytes'] for entry in sizes if entry['variant'] == 'base' and
                        all(entry[key] == row[key] for key in ['fixture', 'optimization', 'encoding']))
        row['delta_from_base_bytes'] = row['bytes'] - baseline
    with (output / 'size.csv').open('w') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(sizes[0]))
        writer.writeheader()
        writer.writerows(sizes)
    (output / 'table-sharing.json').write_text(json.dumps(dict(
        table_bytes=len(table), table_sha256=hashlib.sha256(table).hexdigest(), records=table_records,
        check='Count the complete 2048-byte table in instantiated linear memory, including implicit zero initialization.'), indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    args = parser.parse_args()
    measure(args.work.resolve(), args.output.resolve())
