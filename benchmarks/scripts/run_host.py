"""Build, measure and validate the shared kernel; never infer cycles from nominal MHz."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import uuid

from results import summarize, write_csv

ROOT = Path(__file__).resolve().parents[1]


def output(command):
    return subprocess.check_output(command, text=True).strip()


def read_cpu():
    if platform.system() == 'Darwin':
        return {'board': output(['sysctl', '-n', 'hw.model']),
                'soc': output(['sysctl', '-n', 'machdep.cpu.brand_string']),
                'core': 'OS-scheduled; performance/efficiency core not pinned',
                'raw': output(['sysctl', 'hw.model', 'hw.ncpu', 'machdep.cpu.brand_string'])}
    if platform.system() == 'Windows':
        raw = output(['pwsh', '-NoProfile', '-Command',
                      'Get-CimInstance Win32_Processor | Select-Object Name,Manufacturer,Architecture,NumberOfCores,NumberOfLogicalProcessors | ConvertTo-Json'])
        cpus = json.loads(raw)
        if isinstance(cpus, dict):
            cpus = [cpus]
        return {'board': platform.node(), 'soc': '; '.join(cpu['Name'].strip() for cpu in cpus),
                'core': 'OS-scheduled; affinity not pinned', 'raw': raw}
    cpuinfo = Path('/proc/cpuinfo').read_text()
    model = next((line.split(':', 1)[1].strip() for line in cpuinfo.splitlines()
                  if line.startswith(('model name', 'Model'))), platform.machine())
    board = Path('/sys/devices/virtual/dmi/id/board_name')
    return {'board': board.read_text().strip() if board.exists() else platform.node(),
            'soc': model, 'core': 'OS-scheduled; affinity not pinned', 'raw': cpuinfo}


def build(directory, target_cpu='native'):
    flags = '' if target_cpu == 'default' else '-C target-cpu=' + target_cpu
    env = os.environ.copy() | {'RUSTFLAGS': flags,
                              'CARGO_TARGET_DIR': str(directory / 'target')}
    for name, command in [
        ('build', ['cargo', 'build', '--release', '--locked', '-p', 'pow-bench-host']),
        ('codegen', ['cargo', 'rustc', '--release', '--locked', '-p', 'pow-bench-core', '--', '--emit=llvm-ir,asm']),
    ]:
        with (directory / f'{name}.log').open('w') as log:
            subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    ll = next((directory / 'target/release/deps').glob('pow_bench_core-*.ll')).read_text()
    for suffix in ['ll', 's']:
        shutil.copyfile(next((directory / 'target/release/deps').glob('pow_bench_core-*.' + suffix)),
                        directory / ('core.' + suffix))
    features = sorted(set(re.findall(r'"target-features"="([^"]*)"', ll)))
    cpus = sorted(set(re.findall(r'"target-cpu"="([^"]*)"', ll)))
    if len(cpus) != 1 or len(features) > 1:
        raise ValueError('ambiguous code-generation CPU/features')
    cfg = output(['rustc', '--print', 'cfg', *flags.split()])
    effective = {'cpu_defaults': cpus[0], 'llvm_explicit': features,
                 'rustc_cfg': re.findall(r'target_feature="([^"]*)"', cfg)}
    suffix = '.exe' if platform.system() == 'Windows' else ''
    binary = directory / 'target/release' / ('pow-bench-host' + suffix)
    saved = directory / binary.name
    shutil.copyfile(binary, saved)
    saved.chmod(saved.stat().st_mode | 0o111)
    return saved, cpus[0], json.dumps(effective, sort_keys=True)


def references(directory):
    windows = platform.system() == 'Windows'
    checker = directory / ('mpfr-check.exe' if windows else 'mpfr-check')
    command = ['gcc' if windows else 'cc', '-O2', str(ROOT / 'scripts/accuracy.c'), '-o', str(checker)]
    if platform.system() == 'Darwin':
        for package in ['mpfr', 'gmp']:
            prefix = output(['brew', '--prefix', package])
            command += [f'-I{prefix}/include', f'-L{prefix}/lib']
    subprocess.run(command + ['-lmpfr', '-lgmp', '-lm'], check=True)
    with (directory / 'accuracy.csv').open('w') as csvfile, (directory / 'mpfr.log').open('w') as log:
        subprocess.run([str(checker), str(directory / 'accuracy-bits.csv')],
                       stdout=csvfile, stderr=log, check=True)


def metadata(directory, binary, cpu, features, source_revision, target_cpu='native'):
    compiler = output(['rustc', '-vV'])
    target = next(line[6:] for line in compiler.splitlines() if line.startswith('host: '))
    arch = {'AMD64': 'x86_64', 'ARM64': 'aarch64'}.get(platform.machine(), platform.machine())
    if arch not in {'aarch64', 'arm64', 'x86_64'}:
        raise ValueError(f'host floating-point capability must be verified for {arch}')
    identity = read_cpu()
    candidate_files = sorted((ROOT.parent / 'libm/src/math/pow').glob('*.rs'))
    candidate_files += [ROOT.parent / 'libm/src/math/pow.rs']
    candidate_hash = hashlib.sha256(b''.join(p.read_bytes() for p in candidate_files)).hexdigest()
    data = dict(
        board=identity['board'], soc=identity['soc'], core=identity['core'],
        target_triple=target, target_cpu=cpu, target_features=features,
        float_abi='win64' if platform.system() == 'Windows' else ('aapcs64' if arch in {'aarch64', 'arm64'} else 'sysv-amd64'),
        fpu_mode='hardware_fp64', libc_or_runtime='Rust core/compiler_builtins; ' + target + '; ' + ' '.join(platform.libc_ver()) + '; ' + platform.system(),
        compiler_backend=next(s for s in compiler.splitlines() if s.startswith('LLVM version:')),
        compiler_version=compiler.splitlines()[0], run_id=directory.name,
        device_id=platform.node(), architecture=arch,
        source_sha=output(['git', 'rev-parse', source_revision]),
        firmware_sha=hashlib.sha256(binary.read_bytes()).hexdigest(),
        dataset_sha=json.loads((ROOT / 'vectors/manifest.json').read_text())['sha256'],
        build_flags='opt-level=3,lto=fat,codegen-units=1,panic=abort,target-cpu=' + target_cpu,
        timer='std::time::Instant', timer_hz=1000000000, counter_bits='128 duration representation',
        interrupt_configuration='OS managed', memory_configuration='OS managed; warm caches; no core affinity',
        algorithm_revisions={'Baseline': 'git:6bc104a50f83cb205790c61c5d33508046f5fad3',
                             'Candidate': 'sha256:' + candidate_hash},
    )
    (directory / 'environment.json').write_text(json.dumps(data | {'rustc_vV': compiler, 'cpu_details': identity['raw'],
                                                                'os': platform.platform()}, indent=2) + '\n')
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'results/runs' / str(uuid.uuid4()))
    parser.add_argument('--source-revision', default='HEAD')
    parser.add_argument('--target-cpu', choices=['default', 'native'], default='native')
    args = parser.parse_args()
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    binary, cpu, features = build(directory, args.target_cpu)
    meta = metadata(directory, binary, cpu, features, args.source_revision, args.target_cpu)
    for filename, arguments in [('timing.csv', []), ('accuracy-bits.csv', ['accuracy'])]:
        with (directory / filename).open('w') as f:
            subprocess.run([str(binary), *arguments], stdout=f, check=True)
    references(directory)
    rows = summarize(list(csv.DictReader((directory / 'timing.csv').open())), meta)
    accuracy = {(r['test_distribution'], r['implementation']): r for r in csv.DictReader((directory / 'accuracy.csv').open())}
    for row in rows:
        result = accuracy[row['test_distribution'], row['implementation']]
        row['accuracy_max_ulp'] = result['accuracy_max_ulp']
        row['accuracy_status'] = 'PASS'
    write_csv(directory / 'hosted.csv', rows)
    print(directory)


if __name__ == '__main__':
    main()
