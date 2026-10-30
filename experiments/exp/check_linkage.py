"""Check final pow+exp+exp2 modules with and without link-time optimization."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from size import table_bytes
from validate import execute, ROOT


def check(work, output):
    raw, artifacts = output / 'raw', output / 'artifacts'
    directory = work / 'candidate'
    host = next(line.split(': ', 1)[1] for line in subprocess.check_output(['rustc', '-vV'], text=True).splitlines()
                if line.startswith('host: '))
    table = table_bytes()
    table_path = artifacts / 'EXP_TAB.bin'
    table_path.write_bytes(table)
    results = []
    for lto in ['fat', 'off']:
        destination = directory / f'linkage-{lto}'
        env = os.environ | {'CARGO_TARGET_DIR': str(destination), 'RUSTFLAGS': '',
                            'CARGO_PROFILE_RELEASE_LTO': lto}
        for target in [host, 'wasm32-unknown-unknown']:
            execute(['cargo', 'build', '--manifest-path', directory / 'fixtures/Cargo.toml', '--release',
                     '--lib', '--offline', '--features', 'medium', '--target', target],
                    f'linkage-{lto}-{target}', raw, env=env)
            name = 'exp_fixture.wasm' if target.startswith('wasm') else (
                'libexp_fixture.dylib' if sys.platform == 'darwin' else 'libexp_fixture.so')
            file = destination / target / 'release' / name
            data = file.read_bytes()
            if target.startswith('wasm'):
                inspection = json.loads(subprocess.check_output(
                    ['node', str(ROOT / 'inspect_module.mjs'), str(file), str(table_path)], text=True))
                count = inspection['table_occurrences']
            else:
                count = data.count(table)
                undefined = subprocess.check_output(['nm', '-u', str(file)], text=True)
                (raw / f'linkage-{lto}-{target}-undefined.txt').write_text(undefined)
                forbidden = re.findall(r'(?m)\b_+(?:fma|fmaf|exp|exp2|pow|adddf3|muldf3|divdf3)$', undefined)
                if forbidden:
                    raise ValueError(f'unexpected math/libcall imports: {forbidden}')
                inspection = dict(full_table_binary_occurrences=count, forbidden_libcalls=forbidden)
            if count != 1:
                raise ValueError(f'{target}, LTO {lto}: expected one EXP_TAB, found {count}')
            (artifacts / f'linked-{lto}-{target}{file.suffix}.gz').write_bytes(gzip.compress(data, mtime=0))
            results.append(dict(target_triple=target, lto=lto, sha256=hashlib.sha256(data).hexdigest(),
                                table_occurrences=count, inspection=inspection, status='PASS'))
    (output / 'linkage.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    args = parser.parse_args()
    check(args.work.resolve(), args.output.resolve())
