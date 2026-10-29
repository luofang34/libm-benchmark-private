"""Accept F411 results only after firmware, dataset, FPU and MPFR checks agree."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from results import summarize, write_csv
from run_host import references

ROOT = Path(__file__).resolve().parents[1]


def accept(capture, firmware):
    device = json.loads((capture / 'device.json').read_text())
    manifest = json.loads((firmware / 'manifest.json').read_text())
    expected_dataset = json.loads((ROOT / 'vectors/manifest.json').read_text())
    image_sha = hashlib.sha256((firmware / 'pow-f411.bin').read_bytes()).hexdigest()
    if device['firmware_sha'] != image_sha or image_sha != manifest['firmware_sha']:
        raise ValueError('running firmware differs from the verified flash artifact')
    if device['dataset_sha'] != expected_dataset['sha256']:
        raise ValueError('device used a different input corpus')
    if device['chip_id'] & 0xfff != 0x431 or device['flash_kib'] != 512:
        raise ValueError('unexpected silicon family or Flash capacity')
    if device['fpscr'] & 0x03c00000 or (device['mvfr0'] >> 8) & 15 != 0 or (device['mvfr0'] >> 4) & 15 == 0:
        raise ValueError('FP32/software-FP64 capability or IEEE mode is incorrect')
    payload = (capture / 'payload.bin').read_bytes()
    if hashlib.sha256(payload).hexdigest() != device['payload_sha256']:
        raise ValueError('saved payload integrity check failed')
    if not payload.startswith(b'TIMING\n'):
        raise ValueError('missing timing section')
    timing, accuracy = payload[len(b'TIMING\n'):].split(b'ACCURACY\n', 1)
    (capture / 'timing.csv').write_bytes(timing)
    (capture / 'accuracy-bits.csv').write_bytes(accuracy)
    rows = list(csv.DictReader(accuracy.decode().splitlines()))
    pairs = b''.join(struct.pack('<QQ', int(r['x_bits'], 16), int(r['y_bits'], 16)) for r in rows)
    if len(rows) != expected_dataset['cases'] or hashlib.sha256(pairs).hexdigest() != expected_dataset['sha256']:
        raise ValueError('accuracy stream is missing, reordered or substituted')
    trials = list(csv.DictReader(timing.decode().splitlines()))
    expected = {(domain, mode, str(round_id), implementation)
                for domain in {r['test_distribution'] for r in rows}
                for mode in ['Throughput', 'Dependency'] for round_id in range(15)
                for implementation in ['Baseline', 'Candidate']}
    observed = {(r['test_distribution'], r['mode'], r['round'], r['implementation']) for r in trials}
    if observed != expected or len(trials) != len(expected):
        raise ValueError('timing stream is incomplete or contains duplicate trials')
    if device['hse_hz'] % 1_000_000 or not 4_000_000 <= device['hse_hz'] <= 26_000_000:
        raise ValueError('invalid detected HSE frequency')
    if abs(device['hse_estimate_hz'] - device['hse_hz']) > device['hse_hz'] // 66:
        raise ValueError('ambiguous HSE measurement')
    if device['clock_hz'] != 48_000_000 or any(int(r['timer_hz']) != device['clock_hz'] for r in trials):
        raise ValueError('timer frequency differs from the audited clock configuration')
    references(capture)
    return device, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    parser.add_argument('--firmware', type=Path, default=ROOT / 'firmware/f411')
    args = parser.parse_args()
    device, firmware = accept(args.capture, args.firmware)
    codegen = next(r for r in json.loads((ROOT / 'results/codegen/codegen.json').read_text()) if r['id'] == 'stm32f411')
    sections = firmware['sections']
    compiler = firmware['compiler_version'].splitlines()
    revision = firmware['source_sha']
    files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', revision,
                                     'libm/src/math/pow'], cwd=ROOT.parent, text=True).splitlines()
    files = sorted(p for p in files if p.endswith('.rs')) + ['libm/src/math/pow.rs']
    candidate_source = b''.join(subprocess.check_output(['git', 'show', f'{revision}:{p}'], cwd=ROOT.parent) for p in files)
    ccr = device['scb_ccr']
    metadata = dict(
        board=firmware['board'], soc='STM32F411', core='Cortex-M4F',
        target_triple=firmware['target_triple'], target_cpu=firmware['target_cpu'],
        target_features=json.dumps(codegen['target_features'], sort_keys=True),
        float_abi=firmware['float_abi'], fpu_mode='hardware_fp32_software_fp64',
        libc_or_runtime='cortex-m-rt 0.7.7; Rust compiler_builtins; no libc',
        compiler_backend=next(s for s in compiler if s.startswith('LLVM version:')),
        compiler_version=compiler[0], run_id=device['run_id'] + '-' + device['payload_sha256'][:16], device_id=device['device_id'],
        architecture='Arm', source_sha=firmware['source_sha'], firmware_sha=firmware['firmware_sha'],
        dataset_sha=device['dataset_sha'], build_flags=firmware['build_flags'],
        clock_hz=device['clock_hz'], timer='core_cycles', timer_hz=device['clock_hz'], counter_bits=32,
        interrupt_configuration='PRIMASK=1; USB polled outside timed batches',
        memory_configuration=f"Flash code and tables; SRAM stack; CCR={ccr:#x}; Flash ACR={device['flash_acr']:#x}; HSE nominal={device['hse_hz']}; HSI-based HSE estimate={device['hse_estimate_hz']}",
        text_bytes=sections['.text'], rodata_bytes=sections['.rodata'],
        ram_bytes=sections['.data'] + sections['.bss'], data_bytes=sections['.data'], bss_bytes=sections['.bss'],
        size_scope='whole dual-algorithm firmware; static RAM only; stack not measured',
        algorithm_revisions={'Baseline': 'git:6bc104a50f83cb205790c61c5d33508046f5fad3',
                             'Candidate': 'sha256:' + hashlib.sha256(candidate_source).hexdigest()},
    )
    rows = summarize(list(csv.DictReader((args.capture / 'timing.csv').open())), metadata)
    accuracy = {(r['test_distribution'], r['implementation']): r for r in csv.DictReader((args.capture / 'accuracy.csv').open())}
    for row in rows:
        row['accuracy_max_ulp'] = accuracy[row['test_distribution'], row['implementation']]['accuracy_max_ulp']
        row['accuracy_status'] = 'PASS'
    write_csv(args.capture / 'hardware.csv', rows)
    print(f'Accepted {len(rows)} hardware results after firmware/FPU/MPFR validation')


if __name__ == '__main__':
    main()
