"""Verify saved results, archive exact artifacts, and write a machine-readable evidence index."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from validate import ROOT, execute, locations


def inspect_std(sysroots, output):
    records = []
    for variant in ['base', 'candidate']:
        wasm = sysroots / variant / 'target/wasm32-unknown-unknown/release/exp_experiment.wasm'
        wat = (output / f'raw/sysroot-{variant}.wat').read_text()
        symbols = re.findall(r'^ \(func (\S+)', wat, re.M)
        math_symbols = [name for name in symbols if 'compiler_builtins' in name and 'exp' in name]
        software_fma = [name for name in symbols if 'fma' in name.lower()]
        if len(math_symbols) < 2 or software_fma:
            raise ValueError(f'{variant}: unexpected exp symbols/FMA definitions')
        memory = json.loads(subprocess.check_output(['node', str(ROOT / 'inspect_module.mjs'), str(wasm),
                            str(output / 'artifacts/EXP_TAB.bin'), 'timed'], text=True))
        if variant == 'candidate' and memory['table_occurrences'] != 1:
            raise ValueError('patched std must use one shared table for exp and exp2')
        records.append(dict(variant=variant, compiler_builtins_exp_symbols=math_symbols,
                            software_fma_functions=software_fma, inspection=memory))
    (output / 'std-symbols.json').write_text(json.dumps(records, indent=2) + '\n')


def archive(work, output, status):
    artifacts = output / 'artifacts'
    for runtime, files in locations(work).items():
        for variant, file in zip(['base', 'candidate'], files):
            (artifacts / f'{runtime}-{variant}{file.suffix}.gz').write_bytes(gzip.compress(file.read_bytes(), mtime=0))
    performance = list(csv.DictReader((output / 'performance.csv').open()))
    std_performance = list(csv.DictReader((output / 'performance-std.csv').open()))
    accuracy = list(csv.DictReader((output / 'accuracy.csv').open()))
    std_accuracy = list(csv.DictReader((output / 'accuracy-std.csv').open()))
    for name in ['harness', 'fixture']:
        source = output / f'raw/{name}-base-Cargo.lock'
        if source.read_bytes() != (output / f'raw/{name}-candidate-Cargo.lock').read_bytes():
            raise ValueError(f'{name}: paired builds resolved different dependency locks')
        destination = ROOT / ('fixtures' if name == 'fixture' else name) / 'Cargo.lock'
        shutil.copyfile(source, destination)
    for name in ['performance.csv', 'performance-std.csv']:
        path = output / name
        rows = list(csv.DictReader(path.open()))
        for row in rows:
            row['measurement_status'] = status
        with path.open('w') as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = dict(
        scope='Separate exp/exp2 prototype; the pow-only proposed upstream patch is unchanged.',
        performance_status=status, formal_performance_acceptance=False,
        base_revision='ef357e6075c6d7eca9d2fd72412e43fb5fc1a5ff',
        direct_measurement_groups=len(performance), ordinary_std_measurement_groups=len(std_performance),
        warmups=5, rounds=15, sample_count_per_function_per_runtime=146097,
        candidate_accuracy=[row for row in accuracy + std_accuracy if row['domain'] == 'all' and 'candidate' in row['implementation']],
        shared_table_bytes=2048, final_linkage=json.loads((output / 'linkage.json').read_text()),
        size_comparisons=len(list(csv.DictReader((output / 'size.csv').open()))),
        patched_sysroot_verified=True,
        known_limits=(['Performance collected with background CPU and filesystem activity; requires an idle rerun.']
                      if status == 'exploratory_background_load' else []) +
                     ['No new MCU or remote Linux/Windows hardware run for exp/exp2.',
                      'The full 25-target upstream matrix and full extensive exp/exp2 sweeps have not run.',
                      '256-bit MPFR samples do not prove a global worst-case error bound.',
                      'Only round-to-nearest behavior tested; errno and full fenv behavior are outside this prototype.',
                      'Dependency measurements include bounded feedback and checksum overhead, not pure function latency.'],
        reproducible_entry='python3 experiments/exp/reproduce.py --help',
        metadata='metadata.json', cpu_snapshots=['raw/cpu-before.json', 'raw/cpu-after.json'],
        performance='performance.csv', ordinary_std_performance='performance-std.csv',
        accuracy='accuracy.csv', ordinary_std_accuracy='accuracy-std.csv', sizes='size.csv')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    for directory in [artifacts, output / 'raw']:
        for file in directory.iterdir():
            if file.is_file() and (file.suffix in ['.bin', '.wasm', '.wat'] or file.name in ['domains.txt', 'mpfr-check']):
                (file.parent / f'{file.name}.gz').write_bytes(gzip.compress(file.read_bytes(), mtime=0))
                file.unlink()


def cleanup(work, sysroots, output):
    for directory, kind in [(work, 'work'), (sysroots, 'sysroots')]:
        marker = json.loads((directory / '.exp-validation-owned.json').read_text())
        if marker != dict(path=str(directory.resolve()), kind=kind):
            raise ValueError(f'{directory} is not owned by this experiment')
    for variant in ['base', 'candidate']:
        for subdirectory in ['target', 'fixture-target', 'linkage-fat', 'linkage-off', 'validation-target']:
            target = work / variant / subdirectory
            if target.exists():
                execute(['cargo', 'clean', '--manifest-path', work / variant / 'harness/Cargo.toml',
                         '--target-dir', target], f'cleanup-{variant}-{subdirectory}', output / 'raw')
        target = sysroots / variant / 'target'
        if target.exists():
            execute(['cargo', 'clean', '--manifest-path', sysroots / variant / 'harness/Cargo.toml',
                     '--target-dir', target], f'cleanup-sysroot-{variant}', output / 'raw')
    shutil.rmtree(work)
    shutil.rmtree(sysroots)
    (output / 'cleanup.json').write_text(json.dumps(dict(work_removed=not work.exists(),
        sysroots_removed=not sysroots.exists()), indent=2) + '\n')


def checksums(output):
    records = {str(file.relative_to(output)): hashlib.sha256(file.read_bytes()).hexdigest()
               for file in sorted(output.rglob('*')) if file.is_file() and file != output / 'sha256.json'}
    (output / 'sha256.json').write_text(json.dumps(records, indent=2) + '\n')
    for name, digest in records.items():
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'evidence changed while hashing: {name}')
    print(f'Verified {len(records)} evidence checksums.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--sysroots', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    parser.add_argument('--measurement-status', default='exploratory_background_load')
    args = parser.parse_args()
    work, sysroots, output = args.work.resolve(), args.sysroots.resolve(), args.output.resolve()
    inspect_std(sysroots, output)
    archive(work, output, args.measurement_status)
    cleanup(work, sysroots, output)
    checksums(output)
