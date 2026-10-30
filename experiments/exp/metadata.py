"""Attach explicit host/toolchain metadata, leaving unmeasured hardware quantities empty."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
from validate import ROOT


def collect(output):
    environment = json.loads((output / 'environment.json').read_text())
    commands = environment['commands']
    cpu = commands['cpu']['output'].strip() if commands['cpu']['exit_code'] == 0 else None
    model = subprocess.run(['sysctl', '-n', 'hw.model'], text=True, capture_output=True)
    versions = json.loads(commands['node_v8']['output'])
    targets = {}
    for key in ['aarch64-apple-darwin', 'wasm32-unknown-unknown', 'wasm32-unknown-unknown+nightly']:
        target = key.removesuffix('+nightly')
        compiler = ['rustc', '+nightly'] if key.endswith('+nightly') else ['rustc']
        cfg = subprocess.check_output([*compiler, '--print', 'cfg', '--target', target], text=True)
        spec = json.loads(subprocess.check_output([*compiler, '--print', 'target-spec-json',
            '-Zunstable-options', '--target', target], text=True, env=os.environ | {'RUSTC_BOOTSTRAP': '1'}))
        targets[key] = dict(target_cpu=spec.get('cpu', 'generic'),
            target_features=[line.split('=', 1)[1].strip('"') for line in cfg.splitlines()
                             if line.startswith('target_feature=')], target_cfg=cfg.splitlines(),
            default_target_spec=spec)
    records = {}
    for runtime in ['native', 'wasm_node', 'wasm_sysroot_node']:
        target = 'aarch64-apple-darwin' if runtime == 'native' else 'wasm32-unknown-unknown'
        target_key = target + ('+nightly' if runtime == 'wasm_sysroot_node' else '')
        compiler = commands['rustc']['output']
        if runtime == 'wasm_sysroot_node' and (output / 'std-integration.json').exists():
            compiler = json.loads((output / 'std-integration.json').read_text())['records'][0]['compiler']
        records[runtime] = dict(board=model.stdout.strip() if model.returncode == 0 else None, soc=cpu,
            core='scheduler selected, not pinned', target_triple=target,
            target_cpu=targets[target_key]['target_cpu'], target_features=','.join(targets[target_key]['target_features']),
            float_abi='target default', fpu_mode='process default; FPCR not sampled',
            libc_or_runtime='macOS system runtime' if runtime == 'native' else f"Node {versions['node']} / V8 {versions['v8']}",
            compiler_backend=next(line for line in compiler.splitlines() if line.startswith('LLVM version:')),
            compiler_version=compiler.splitlines()[0], cycles_per_op=None, text_bytes=None,
            rodata_bytes=None, ram_bytes=None)
    record = dict(runtimes=records, targets=targets,
        cpu_snapshots=['raw/cpu-before.json', 'raw/cpu-after.json'],
        unmeasured_fields={'cycles_per_op': 'No hardware cycle counter was sampled.',
                          'text_bytes': 'See size.csv for whole-module raw/compressed size, not section attribution.',
                          'rodata_bytes': 'The shared table is 2048 bytes; complete section attribution was not measured.',
                          'ram_bytes': 'No runtime peak-memory measurement.'},
        reference_precision_bits=256, rounding='nearest',
        dependency_kernel='Result bits perturb the next input or special-value address; includes feedback/checksum overhead.',
        timing='Inputs allocated/generated before timing; full loop in Rust; 5 warmups then 15 interleaved rounds; inclusive p10/p90.',
        accuracy_scope='Observed corpus evidence, not a proof of a global worst-case bound.')
    (output / 'metadata.json').write_text(json.dumps(record, indent=2) + '\n')
    return records


def enrich(output, records):
    sources = {variant: json.loads((output / f'raw/source-{variant}.json').read_text()) for variant in ['base', 'candidate']}
    revision = {variant: hashlib.sha256(json.dumps(source['source_sha256'], sort_keys=True).encode()).hexdigest()
                for variant, source in sources.items()}
    for performance, accuracy in [('performance.csv', 'accuracy.csv'), ('performance-std.csv', 'accuracy-std.csv')]:
        path = output / performance
        if not path.exists():
            continue
        rows = list(csv.DictReader(path.open()))
        accuracy_rows = list(csv.DictReader((output / accuracy).open()))
        for row in rows:
            row.update(records[row['runtime']])
            candidate = 'candidate' in row['implementation']
            row['algorithm_revision'] = 'source-manifest-sha256:' + revision['candidate' if candidate else 'base']
            if row['implementation'].startswith('std_') and row['implementation'] not in ['std_rebuilt_base', 'std_rebuilt_candidate']:
                row['algorithm_revision'] = row['compiler_version'] if 'wasm' in row['runtime'] else 'macOS system libsystem_m'
            if row['implementation'] == 'control':
                row['algorithm_revision'] = 'x + 1.0 harness control'
            row['test_distribution'] = row['domain']
            row['ns_per_op'] = row['median_ns']
            row['speedup'] = row['speedup_vs_baseline']
            name = row['implementation']
            if name in ['std_system', 'std_prebuilt_sysroot']:
                name = 'std'
            found = [value for value in accuracy_rows if value['function'] == row['function'] and
                     value['implementation'] == name and value['domain'] == 'all' and
                     value['runtime'] == {'wasm_node': 'wasm'}.get(row['runtime'], row['runtime'])]
            row['accuracy_max_ulp'] = found[0]['max_ulp'] if found else None
        with path.open('w') as destination:
            writer = csv.DictWriter(destination, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    args = parser.parse_args()
    destination = args.output.resolve()
    enrich(destination, collect(destination))
