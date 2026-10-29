"""Audit CPU-specific arithmetic lowering without presenting objects as flashable firmware."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build(profile, directory):
    destination = directory / profile['id']
    destination.mkdir(parents=True, exist_ok=True)
    target_dir = destination / 'target'
    flags = '-C target-cpu=' + profile['target_cpu']
    if profile['requested_target_features']:
        flags += ' -C target-feature=' + profile['requested_target_features']
    env = os.environ.copy() | {'RUSTFLAGS': flags, 'CARGO_TARGET_DIR': str(target_dir)}
    toolchain = profile.get('toolchain', 'stable')
    cmd = ['cargo', '+' + toolchain, 'rustc', '--release', '--locked', '-p', 'pow-bench-core',
           '--target', profile['target_triple']]
    if toolchain == 'esp':
        cmd += ['-Z', 'build-std=core']
    cmd += ['--', '--emit=llvm-ir,asm,obj']
    with (destination / 'build.log').open('w') as log:
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    record = profile | {'scope': 'unlinked code-generation objects; no board/ABI runtime validation',
                        'command': cmd, 'RUSTFLAGS': flags,
                        'compiler_version': subprocess.check_output(['rustc', '+' + toolchain, '-vV'], text=True)}
    if result.returncode:
        return record | {'codegen_status': 'BLOCKED', 'reason': 'cross-compile failed; see build.log'}
    artifacts = target_dir / profile['target_triple'] / 'release/deps'
    assembly = next(artifacts.glob('pow_bench_core-*.s')).read_text()
    ir = next(artifacts.glob('pow_bench_core-*.ll')).read_text()
    for path in artifacts.glob('pow_bench_core-*'):
        if path.suffix in {'.s', '.ll', '.o'}:
            shutil.copyfile(path, destination / ('core' + path.suffix))
    features = sorted(set(re.findall(r'"target-features"="([^"]*)"', ir)))
    record['emitted_target_cpus'] = sorted(set(re.findall(r'"target-cpu"="([^"]*)"', ir)))
    record['target_features'] = {'cpu_defaults': record['emitted_target_cpus'],
                                 'llvm_explicit': features,
                                 'requested_extra': profile['requested_target_features']}
    record['fp32_instruction_lines'] = [s.strip() for s in assembly.splitlines()
                                       if re.search(r'v(?:mul|div|add|mla)\.f32|f(?:mul|div|add)\.s|mul\.s', s)]
    record['fp64_instruction_lines'] = [s.strip() for s in assembly.splitlines()
                                       if re.search(r'v(?:mul|div|add|mla)\.f64|f(?:mul|div|add)\.d', s)]
    record['fp64_helper_lines'] = [s.strip() for s in assembly.splitlines()
                                  if re.search(r'__aeabi_d(?:mul|div|add)|__(?:mul|div|add)df3', s)]
    record['fp32_helper_lines'] = [s.strip() for s in assembly.splitlines()
                                  if re.search(r'__aeabi_f(?:mul|div|add)|__(?:mul|div|add)sf3', s)]
    expected = profile['expected_fpu_mode']
    fp32, fp64 = bool(record['fp32_instruction_lines']), bool(record['fp64_instruction_lines'])
    helpers = bool(record['fp64_helper_lines'])
    valid = (expected == 'hardware_fp64' and fp32 and fp64) or (
        expected == 'hardware_fp32_software_fp64' and fp32 and not fp64 and helpers) or (
        expected == 'software_fp32_fp64' and not fp32 and not fp64 and helpers and record['fp32_helper_lines'])
    record['codegen_status'] = 'PASS' if valid else 'FAIL'
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    profiles = json.loads((ROOT / 'boards/profiles.json').read_text())
    records = []
    for profile in profiles:
        if profile.get('deferred') or profile.get('optional'):
            continue
        record = build(profile, args.output.resolve())
        records.append(record)
        (args.output / 'codegen.json').write_text(json.dumps(records, indent=2) + '\n')
        print(profile['id'], record['codegen_status'], flush=True)
    if any(r['codegen_status'] == 'FAIL' for r in records):
        raise ValueError('arithmetic code generation does not match the requested capability')


if __name__ == '__main__':
    main()
