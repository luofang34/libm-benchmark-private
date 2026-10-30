"""Reproduce the macOS/Node prototype: source, builds, sizes, linkage, MPFR, direct and rebuilt std timing.

All phases: python3 experiments/exp/reproduce.py --work /tmp/exp-run --sysroots /tmp/exp-sysroots
Build/measure can be separated with --phase build, then --phase measure using the same paths.
The measure/all phase archives artifacts and cargo-cleans/removes both temporary directories.
Requires Rust 1.99 with wasm32 std, nightly 41089d07 with rust-src, Node, Clang, Homebrew MPFR,
gzip, Brotli and Binaryen. Existing cached Cargo dependencies are used offline.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request
import check_linkage
import check_records
import finalize
import metadata
from prepare import ARM_REVISION
import size
import validate
import validate_std

ROOT = Path(__file__).resolve().parent


def arm_source(work):
    source = ROOT.parent / 'pow/vendor/optimized-routines/math'
    expected = json.loads((ROOT / 'arm-source-sha256.json').read_text())
    if not source.exists():
        url = f'https://codeload.github.com/ARM-software/optimized-routines/tar.gz/{ARM_REVISION}'
        with urllib.request.urlopen(url) as response:
            content = response.read()
        with tarfile.open(fileobj=io.BytesIO(content)) as archive:
            archive.extractall(work / 'arm-reference', filter='data')
        source = work / f'arm-reference/optimized-routines-{ARM_REVISION}/math'
    for name, digest in expected.items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'ARM reference differs from pinned source: {name}')
    return source


def cpu_snapshot(output, name):
    records = {}
    for label, command in [('processes', ['ps', '-Ao', 'pid,pcpu,comm']), ('cpu', ['top', '-l', '1', '-n', '0'])]:
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        records[label] = dict(command=command, exit_code=result.returncode, output=result.stdout)
    (output / f'raw/cpu-{name}.json').write_text(json.dumps(records, indent=2) + '\n')


def library_checks(work, output):
    manifest = work / 'candidate/libm/Cargo.toml'
    env = os.environ | {'CARGO_TARGET_DIR': str(work / 'candidate/validation-target'), 'RUSTFLAGS': ''}
    for label, args in [('library-tests', ['test', '--lib']), ('library-clippy', ['clippy', '--all-targets'])]:
        command = ['cargo', *args, '--manifest-path', manifest, '--offline']
        if label.endswith('clippy'):
            command += ['--', '-Dwarnings']
        validate.execute(command, label, output / 'raw', env=env)
    for target in ['thumbv6m-none-eabi', 'riscv32imac-unknown-none-elf']:
        validate.execute(['cargo', 'build', '--manifest-path', manifest, '--lib', '--release', '--offline',
                          '--no-default-features', '--target', target], f'fallback-{target}', output / 'raw', env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--work', type=Path, required=True, help='Absent temporary source/build directory')
    parser.add_argument('--sysroots', type=Path, required=True, help='Absent temporary sysroot directory')
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    parser.add_argument('--phase', choices=['all', 'build', 'measure', 'archive'], default='all')
    parser.add_argument('--measurement-status', choices=['exploratory_background_load', 'idle_rerun'],
                        default='exploratory_background_load', help='Record actual host conditions; does not certify the run')
    args = parser.parse_args()
    work, sysroots, output = args.work.resolve(), args.sysroots.resolve(), args.output.resolve()
    for name in ['raw', 'artifacts']:
        (output / name).mkdir(parents=True, exist_ok=True)
    if args.phase in ['all', 'build']:
        validate.environment(output)
        validate.stage(work, output / 'raw')
        validate.build(work, output / 'raw')
        library_checks(work, output)
        size.measure(work, output)
        check_linkage.check(work, output)
        validate_std.build(work, sysroots, output)
    if args.phase in ['all', 'measure']:
        validate.accuracy(validate.locations(work), output / 'raw', output / 'artifacts', output, arm_source(work))
        check_records.check(output)
        cpu_snapshot(output, 'before')
        validate.performance(validate.locations(work), output / 'raw', output)
        validate_std.measure(sysroots, output)
        cpu_snapshot(output, 'after')
    if args.phase in ['all', 'measure', 'archive']:
        metadata.enrich(output, metadata.collect(output))
        finalize.inspect_std(sysroots, output)
        finalize.archive(work, output, args.measurement_status)
        finalize.cleanup(work, sysroots, output)
        finalize.checksums(output)


if __name__ == '__main__':
    main()
