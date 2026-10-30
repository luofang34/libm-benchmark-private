"""Build pinned source variants and reproduce native/WASM performance and MPFR checks."""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def execute(command, label, raw, *, env=None, output=None):
    command = [str(part) for part in command]
    started = time.monotonic()
    with (raw / f'{label}.log').open('w') as log:
        if output:
            with output.open('w') as destination:
                result = subprocess.run(command, env=env, stdout=destination, stderr=log)
        else:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
    (raw / f'{label}.json').write_text(json.dumps(dict(command=command, exit_code=result.returncode,
        elapsed_seconds=time.monotonic() - started), indent=2) + '\n')
    print(label, result.returncode, flush=True)
    result.check_returncode()


def stage(work, raw):
    if work.exists() and any(work.iterdir()):
        raise ValueError(f'{work} must be absent or empty')
    work.mkdir(parents=True, exist_ok=True)
    (work / '.exp-validation-owned.json').write_text(json.dumps(dict(path=str(work.resolve()), kind='work')))
    for variant in ['base', 'candidate']:
        directory = work / variant
        execute([sys.executable, ROOT / 'prepare.py', directory, '--variant', variant],
                f'prepare-{variant}', raw)
        shutil.copytree(ROOT / 'harness', directory / 'harness',
                        ignore=shutil.ignore_patterns('target', 'Cargo.lock'))
        manifest = directory / 'harness/Cargo.toml'
        manifest.write_text(manifest.read_text().replace('path = "../../../libm"', 'path = "../libm"'))
        shutil.copyfile(directory / 'source-manifest.json', raw / f'source-{variant}.json')


def build(work, raw):
    for variant in ['base', 'candidate']:
        directory = work / variant
        shutil.copytree(ROOT / 'harness', directory / 'harness', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('target', 'Cargo.lock'))
        manifest = directory / 'harness/Cargo.toml'
        manifest.write_text(manifest.read_text().replace('path = "../../../libm"', 'path = "../libm"'))
        env = os.environ | {'CARGO_TARGET_DIR': str(directory / 'target'), 'RUSTFLAGS': ''}
        for target in ['native', 'wasm32-unknown-unknown']:
            command = ['cargo', 'build', '--manifest-path', manifest, '--release', '--lib', '--offline']
            if target != 'native':
                command += ['--target', target]
            execute(command, f'build-{variant}-{target}', raw, env=env)
        execute(['cargo', 'fmt', '--manifest-path', manifest, '--check'], f'fmt-{variant}', raw)
        execute(['cargo', 'clippy', '--manifest-path', manifest, '--all-targets', '--offline', '--', '-Dwarnings'],
                f'clippy-{variant}', raw, env=env)
        execute(['cargo', 'doc', '--manifest-path', manifest, '--no-deps', '--all-features', '--offline'],
                f'doc-{variant}', raw, env=env | {'RUSTDOCFLAGS': '-D missing_docs -D broken_intra_doc_links'})
        shutil.copyfile(directory / 'harness/Cargo.lock', raw / f'harness-{variant}-Cargo.lock')


def locations(work):
    extension = '.dylib' if sys.platform == 'darwin' else '.so'
    return {
        runtime: [work / variant / 'target' / path for variant in ['base', 'candidate']]
        for runtime, path in [('native', Path('release') / f'libexp_experiment{extension}'),
                              ('wasm', Path('wasm32-unknown-unknown/release/exp_experiment.wasm'))]
    }


def performance(paths, raw, output):
    execute([sys.executable, ROOT / 'bench_native.py', *paths['native']], 'bench-native', raw,
            output=raw / 'performance-native.csv')
    execute(['node', ROOT / 'bench_wasm.mjs', *paths['wasm']], 'bench-wasm', raw,
            output=raw / 'performance-wasm.csv')
    execute([sys.executable, ROOT / 'summarize.py', raw / 'performance-native.csv',
             raw / 'performance-wasm.csv', '--output', output / 'performance.csv'], 'summarize', raw)


def accuracy(paths, raw, artifacts, output, arm=None):
    execute([sys.executable, ROOT / 'accuracy_inputs.py', artifacts], 'accuracy-inputs', raw)
    for runtime, evaluator in [('native', [sys.executable, ROOT / 'accuracy_native.py']),
                               ('wasm', ['node', ROOT / 'accuracy_wasm.mjs'])]:
        execute([*evaluator, artifacts / 'inputs.bin', *paths[runtime], artifacts / f'{runtime}-outputs.bin'],
                f'accuracy-{runtime}', raw)
    arm = arm or ROOT.parent / 'pow/vendor/optimized-routines/math'
    command = ['clang', '-O3', '-fno-builtin-exp', '-fno-builtin-exp2', '-ffp-contract=off',
               '-DHAVE_FAST_FMA=0', '-DHAVE_FAST_ROUND=0', '-DUSE_GLIBC_ABI=0', '-DWANT_ROUNDING=0',
               '-Dexp=arm_exp', '-Dexp2=arm_exp2', '-I', arm, '-I', arm / 'include',
               '-I', '/opt/homebrew/include', ROOT / 'mpfr_check.c']
    command += [arm / name for name in ['exp.c', 'exp2.c', 'exp_data.c', 'math_err.c']]
    command += ['-L', '/opt/homebrew/lib', '-lmpfr', '-lgmp', '-o', artifacts / 'mpfr-check']
    execute(command, 'build-mpfr', raw)
    rows = []
    for runtime in ['native', 'wasm']:
        execute([artifacts / 'mpfr-check', artifacts / f'{runtime}-outputs.bin', artifacts / 'domains.txt'],
                f'mpfr-{runtime}', raw, output=raw / f'accuracy-{runtime}.csv')
        rows.extend(dict(runtime=runtime) | row for row in csv.DictReader((raw / f'accuracy-{runtime}.csv').open()))
    with (output / 'accuracy.csv').open('w') as destination:
        writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    candidate = [row for row in rows if row['implementation'] == 'libm_candidate' and row['domain'] == 'all']
    expected = json.loads((artifacts / 'corpus.json').read_text())['per_function']
    if len(candidate) != 4 or {(row['runtime'], row['function']) for row in candidate} != {
            (runtime, function) for runtime in ['native', 'wasm'] for function in ['exp', 'exp2']}:
        raise ValueError('missing or duplicated candidate accuracy summary')
    if any(int(row['count']) != expected for row in rows if row['domain'] == 'all'):
        raise ValueError('accuracy output does not contain the complete generated corpus')
    if any(int(row['class_mismatch']) or int(row['signed_zero_mismatch']) or
           float(row['max_ulp']) > 1 for row in candidate):
        raise ValueError(f'candidate accuracy check failed: {candidate}')


def environment(output):
    commands = {'rustc': ['rustc', '-vV'], 'cargo': ['cargo', '-V'], 'clang': ['clang', '--version'],
                'node_v8': ['node', '-p', 'JSON.stringify(process.versions)'],
                'cpu': ['sysctl', '-n', 'machdep.cpu.brand_string'], 'system': ['sw_vers']}
    record = dict(platform=platform.platform(), commands={})
    for name, command in commands.items():
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        record['commands'][name] = dict(command=command, exit_code=result.returncode, output=result.stdout)
    (output / 'environment.json').write_text(json.dumps(record, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    parser.add_argument('--phase', choices=['all', 'build', 'measure'], default='all')
    args = parser.parse_args()
    work, output = args.work.resolve(), args.output.resolve()
    raw, artifacts = output / 'raw', output / 'artifacts'
    raw.mkdir(parents=True, exist_ok=True)
    artifacts.mkdir(parents=True, exist_ok=True)
    environment(output)
    if args.phase in ['all', 'build']:
        stage(work, raw)
        build(work, raw)
    if args.phase in ['all', 'measure']:
        paths = locations(work)
        performance(paths, raw, output)
        accuracy(paths, raw, artifacts, output)
        for runtime, files in paths.items():
            for variant, file in zip(['base', 'candidate'], files):
                data = file.read_bytes()
                (artifacts / f'{runtime}-{variant}{file.suffix}.gz').write_bytes(gzip.compress(data, mtime=0))
        for file in artifacts.glob('*.bin'):
            (file.parent / f'{file.name}.gz').write_bytes(gzip.compress(file.read_bytes(), mtime=0))
            file.unlink()
        checksum = {str(file.relative_to(output)): hashlib.sha256(file.read_bytes()).hexdigest()
                    for file in sorted(output.rglob('*')) if file.is_file()}
        (output / 'sha256.json').write_text(json.dumps(checksum, indent=2) + '\n')


if __name__ == '__main__':
    main()
