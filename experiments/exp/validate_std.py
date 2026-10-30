"""Build paired isolated sysroots, then measure ordinary f64::exp/exp2 calls."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from validate import execute, ROOT

RUST_REVISION = '41089d07a0a2afc16adfe28a760d94d73d7298a4'


def build(work, destination, output):
    raw = output / 'raw'
    version = subprocess.check_output(['rustc', '+nightly', '-vV'], text=True)
    if RUST_REVISION not in version:
        raise ValueError(f'nightly compiler differs from pinned sysroot compiler: {version}')
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f'{destination} must be absent or empty')
    destination.mkdir(parents=True, exist_ok=True)
    (destination / '.exp-validation-owned.json').write_text(json.dumps(dict(path=str(destination.resolve()), kind='sysroots')))
    sysroot = Path(subprocess.check_output(['rustc', '+nightly', '--print', 'sysroot'], text=True).strip())
    installed = sysroot / 'lib/rustlib/src/rust/library'
    records = []
    for variant in ['base', 'candidate']:
        root = destination / variant
        if root.exists():
            raise ValueError(f'{root} must not exist: distinct clean sysroots are required')
        library = root / 'library'
        shutil.copytree(installed, library)
        embedded = library / 'compiler-builtins/libm'
        shutil.rmtree(embedded)
        shutil.copytree(work / variant / 'libm', embedded)
        shutil.copytree(ROOT / 'harness', root / 'harness', ignore=shutil.ignore_patterns('target', 'Cargo.lock'))
        manifest = root / 'harness/Cargo.toml'
        manifest.write_text(manifest.read_text().replace('path = "../../../libm"',
                            'path = "../library/compiler-builtins/libm"'))
        env = os.environ | {'CARGO_TARGET_DIR': str(root / 'target'), 'RUSTFLAGS': '',
                            '__CARGO_TESTS_ONLY_SRC_ROOT': str(library)}
        execute(['cargo', '+nightly', 'build', '--manifest-path', manifest, '--release', '--lib',
                 '--no-default-features', '--target', 'wasm32-unknown-unknown',
                 '-Zbuild-std=std,panic_abort', '--offline', '-vv'], f'sysroot-build-{variant}', raw, env=env)
        source_hashes = {str(path.relative_to(embedded)): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sorted(embedded.rglob('*')) if path.is_file()}
        expected = json.loads((work / variant / 'source-manifest.json').read_text())['source_sha256']
        if source_hashes != {key.removeprefix('libm/'): value for key, value in expected.items()}:
            raise ValueError(f'{variant}: embedded compiler-builtins/libm differs from prepared source')
        wasm = root / 'target/wasm32-unknown-unknown/release/exp_experiment.wasm'
        execute(['wasm-dis', wasm, '-o', raw / f'sysroot-{variant}.wat'], f'sysroot-disassemble-{variant}', raw)
        records.append(dict(variant=variant, compiler=version, sysroot_source=str(library),
            compiler_builtins_libm_source=str(embedded), source_sha256=source_hashes,
            wasm_sha256=hashlib.sha256(wasm.read_bytes()).hexdigest(),
            direct_libm_dependency_enabled=False, cargo_target_dir=str(root / 'target')))
    (output / 'std-integration.json').write_text(json.dumps(dict(records=records,
        meaning='Both variants rebuild compiler-builtins from isolated sysroot sources; the harness only calls ordinary f64 methods.'), indent=2) + '\n')


def measure(destination, output):
    raw, artifacts = output / 'raw', output / 'artifacts'
    modules = [destination / variant / 'target/wasm32-unknown-unknown/release/exp_experiment.wasm'
               for variant in ['base', 'candidate']]
    execute(['node', ROOT / 'bench_wasm.mjs', *modules, '32', 'sysroot'], 'bench-sysroot', raw,
            output=raw / 'performance-sysroot.csv')
    execute([sys.executable, ROOT / 'summarize.py', raw / 'performance-sysroot.csv',
             '--output', output / 'performance-std.csv'], 'summarize-sysroot', raw)
    accuracy(destination, output)


def accuracy(destination, output):
    raw, artifacts = output / 'raw', output / 'artifacts'
    modules = [destination / variant / 'target/wasm32-unknown-unknown/release/exp_experiment.wasm'
               for variant in ['base', 'candidate']]
    execute(['node', ROOT / 'accuracy_wasm.mjs', artifacts / 'inputs.bin', *modules,
             artifacts / 'sysroot-outputs.bin'], 'accuracy-sysroot', raw)
    execute([artifacts / 'mpfr-check', artifacts / 'sysroot-outputs.bin', artifacts / 'domains.txt'],
            'mpfr-sysroot', raw, output=raw / 'accuracy-sysroot.csv')
    rows = []
    for row in csv.DictReader((raw / 'accuracy-sysroot.csv').open()):
        if row['implementation'] == 'std':
            continue
        row['implementation'] = {'libm_base': 'std_rebuilt_base', 'libm_candidate': 'std_rebuilt_candidate',
                                 'arm_c': 'arm_c'}[row['implementation']]
        rows.append(dict(runtime='wasm_sysroot_node') | row)
    with (output / 'accuracy-std.csv').open('w') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    candidate = [row for row in rows if row['implementation'] == 'std_rebuilt_candidate' and row['domain'] == 'all']
    expected = json.loads((artifacts / 'corpus.json').read_text())['per_function']
    if len(candidate) != 2 or {row['function'] for row in candidate} != {'exp', 'exp2'}:
        raise ValueError('missing or duplicated candidate sysroot accuracy summary')
    if any(int(row['count']) != expected for row in rows if row['domain'] == 'all'):
        raise ValueError('sysroot accuracy output does not contain the complete generated corpus')
    if any(int(row['class_mismatch']) or int(row['signed_zero_mismatch']) or
           float(row['max_ulp']) > 1 for row in candidate):
        raise ValueError(f'candidate sysroot accuracy check failed: {candidate}')
    for variant, module in zip(['base', 'candidate'], modules):
        (artifacts / f'sysroot-{variant}.wasm.gz').write_bytes(gzip.compress(module.read_bytes(), mtime=0))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True, help='Prepared base/candidate libm directory from validate.py')
    parser.add_argument('--sysroots', type=Path, required=True, help='New directory for isolated copied Rust sources and builds')
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    parser.add_argument('--phase', choices=['all', 'build', 'measure'], default='all')
    args = parser.parse_args()
    if args.phase in ['all', 'build']:
        build(args.work.resolve(), args.sysroots.resolve(), args.output.resolve())
    if args.phase in ['all', 'measure']:
        measure(args.sysroots.resolve(), args.output.resolve())
