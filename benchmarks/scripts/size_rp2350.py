"""Audit separately linked replacement costs for each RP2350 runtime."""
import argparse
import csv
import json
import subprocess

from build_rp2350 import MODES, ROOT, build, flags


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=MODES)
    args = parser.parse_args()
    directory = ROOT / 'results/runs' / ('rp2350-' + args.mode + '-size')
    triple, cpu, abi, fpu = MODES[args.mode]
    rows = []
    for implementation in ['Baseline', 'Candidate']:
        result = build(args.mode, directory / implementation, implementation)
        sections = result['sections']
        rows.append(dict(board='RP2350 A2', target_cpu=cpu, target_triple=triple,
            float_abi=abi, fpu_mode=fpu, implementation=implementation,
            text_bytes=sections['.text'], rodata_bytes=sections['.rodata'], data_bytes=sections['.data'],
            bss_bytes=sections['.bss'], ram_bytes=sections['.data'] + sections['.bss'], stack_bytes='',
            vector_bytes=sections.get('.vector_table', ''), flash_bytes=result['firmware_bytes'],
            firmware_sha=result['firmware_sha'],
            size_scope='single-algorithm compute fixture; XIP Flash code/constants; no telemetry; static RAM only'))
    baseline = rows[0].copy()
    for row in rows:
        for field in ['text_bytes', 'rodata_bytes', 'data_bytes', 'bss_bytes', 'ram_bytes', 'flash_bytes']:
            row['delta_' + field] = row[field] - baseline[field]
    with (directory / 'memory.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(build_flags=flags(args.mode), compiler_version=subprocess.check_output(['rustc', '-vV'], text=True),
                    source_sha=subprocess.check_output(['git', 'rev-parse', 'experiment/pow-wasm'], text=True).strip(),
                    dataset_sha=(ROOT / 'vectors/timing.sha256').read_text().strip(), rows=rows)
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
