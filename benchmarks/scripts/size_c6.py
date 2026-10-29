"""Audit separately linked replacement costs for the ESP32-C6 ROM software runtime."""
import csv
import json
import subprocess

from build_c6 import ROOT, TARGET, FLAGS, build


def main():
    directory = ROOT / 'results/runs/esp32c6-size'
    triple, cpu, abi, fpu = TARGET, 'generic-rv32', 'ilp32', 'software_fp32_fp64'
    rows = []
    for implementation in ['Baseline', 'Candidate']:
        result = build(directory / implementation, implementation)
        sections = result['sections']
        rows.append(dict(board='ESP32-C6 v0.1', target_cpu=cpu, target_triple=triple,
            float_abi=abi, fpu_mode=fpu, implementation=implementation,
            text_bytes=sections['.text'] + sections['.rwtext'] + sections['.trap'], rodata_bytes=sections['.rodata'] + sections['.rodata_desc'], data_bytes=sections['.data'],
            bss_bytes=sections['.bss'], ram_bytes=sections['.data'] + sections['.bss'] + sections['.rwtext'] + sections['.trap'], stack_bytes='',
            vector_bytes=sections.get('.vector_table', ''), flash_bytes=result['firmware_bytes'],
            firmware_sha=result['firmware_sha'],
            size_scope='single-algorithm compute fixture; Flash code/constants; ROM FP helpers; static RAM includes IRAM code; no telemetry'))
    baseline = rows[0].copy()
    for row in rows:
        for field in ['text_bytes', 'rodata_bytes', 'data_bytes', 'bss_bytes', 'ram_bytes', 'flash_bytes']:
            row['delta_' + field] = row[field] - baseline[field]
    with (directory / 'memory.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    manifest = dict(build_flags=FLAGS, compiler_version=subprocess.check_output(['rustc', '-vV'], text=True),
                    source_sha=subprocess.check_output(['git', 'rev-parse', 'experiment/pow-wasm'], text=True).strip(),
                    dataset_sha=(ROOT / 'vectors/timing.sha256').read_text().strip(), rows=rows)
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
