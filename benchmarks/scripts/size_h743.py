"""Link single-algorithm H743 fixtures and audit actual section replacement costs."""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from build_h743 import BOARD, FLAGS, ROOT, tool


def build(implementation, directory):
    features = 'size-candidate' if implementation == 'Candidate' else 'size-fixture'
    env = os.environ.copy() | {'RUSTFLAGS': FLAGS}
    options = ['--manifest-path', str(BOARD / 'Cargo.toml'), '--locked', '--release',
               '--target', 'thumbv7em-none-eabihf', '--bin', 'pow-size', '--features', features]
    for command in ['clippy', 'build']:
        with (directory / f'{implementation}-{command}.log').open('w') as log:
            subprocess.run(['cargo', command, *options, *(['--', '-D', 'warnings'] if command == 'clippy' else [])],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    elf = BOARD / 'target/thumbv7em-none-eabihf/release/pow-size'
    shutil.copyfile(elf, directory / f'{implementation}.elf')
    reports = {}
    for name, command in [('sections', [tool('size'), '-A']), ('symbols', [tool('nm'), '-S', '--demangle']),
                          ('assembly', [tool('objdump'), '-d', '--demangle', '--mcpu=cortex-m7'])]:
        reports[name] = subprocess.check_output(command + [str(elf)], text=True)
        (directory / f'{implementation}-{name}.txt').write_text(reports[name])
    selected = implementation.lower() + '_pow'
    unwanted = 'candidate_pow' if implementation == 'Baseline' else 'baseline_pow'
    if unwanted in reports['symbols'] or not re.search(r'\bbl\s+.*' + selected, reports['assembly']):
        raise ValueError('fixture does not execute exactly the selected implementation')
    if not re.search(r'v(?:add|mul|div|sub)\.f64', reports['assembly']):
        raise ValueError('FP64 operations missing from linked size fixture')
    sections = {name: int(size) for name, size in re.findall(r'^(\.[\w.]+)\s+(\d+)\s+\d+', reports['sections'], re.M)}
    binary = directory / f'{implementation}.bin'
    subprocess.run([tool('objcopy'), '-O', 'binary', str(elf), str(binary)], check=True)
    return dict(board='STM32H743', target_cpu='cortex-m7', target_triple='thumbv7em-none-eabihf',
                float_abi='aapcs-vfp', fpu_mode='hardware_fp64', implementation=implementation,
                text_bytes=sections['.text'], rodata_bytes=sections['.rodata'], data_bytes=sections['.data'],
                bss_bytes=sections['.bss'], ram_bytes=sections['.data'] + sections['.bss'], stack_bytes='',
                vector_bytes=sections['.vector_table'], flash_bytes=binary.stat().st_size,
                firmware_sha=hashlib.sha256(binary.read_bytes()).hexdigest(),
                size_scope='single-algorithm compute fixture; Flash code/constants; no telemetry; static RAM only')


def main():
    directory = ROOT / 'results/runs/h743-size'
    directory.mkdir(parents=True, exist_ok=True)
    rows = [build(implementation, directory) for implementation in ['Baseline', 'Candidate']]
    baseline = rows[0].copy()
    for row in rows:
        for field in ['text_bytes', 'rodata_bytes', 'data_bytes', 'bss_bytes', 'ram_bytes', 'flash_bytes']:
            row['delta_' + field] = row[field] - baseline[field]
    with (directory / 'memory.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(build_flags=FLAGS, compiler_version=subprocess.check_output(['rustc', '-vV'], text=True),
                    source_sha=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                    dataset_sha=(ROOT / 'vectors/timing.sha256').read_text().strip(), rows=rows)
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
