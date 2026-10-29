"""Accept RP2040 software-floating-point results only with verified cycle intervals."""
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


def capability(device, manifest):
    if (device['cpuid'] >> 4) & 0xfff != 0xc60 or device['rom_version'] != 3:
        raise ValueError('unexpected Cortex-M0+ or RP2040 ROM identity')
    if device['chip_id'] >> 28 != 2:
        raise ValueError('unexpected RP2040 silicon revision')
    if device['systick_csr'] & 7 != 5:
        raise ValueError('SysTick must use the processor clock without interrupts')
    hz = device['clock_hz']
    if hz != 125_000_000 or abs(device['sof_clock_hz'] - hz) > hz // 200:
        raise ValueError('core cycle counter disagrees with USB frame clock')
    if not 0 < device['max_batch_us'] < 100_000:
        raise ValueError('ambiguous 24-bit SysTick interval')
    if device['spi_baud'] != 4 or device['spi_ctrl'] >> 24 != 3:
        raise ValueError('Flash configuration differs from generic 03h boot2')


def check_intervals(trials, device):
    for row in trials:
        micros, ticks = int(row['batch_us']), int(row['ticks'])
        if not 0 < micros <= device['max_batch_us'] < 100_000 or not 0 < ticks < 1 << 24:
            raise ValueError('ambiguous 24-bit SysTick interval')
        expected = micros * (device['clock_hz'] // 1_000_000)
        if abs(ticks - expected) > max(512, expected // 50):
            raise ValueError('SysTick cycle interval disagrees with independent timer')


def accept(capture, firmware, record_accuracy_failure=False):
    device = json.loads((capture / 'device.json').read_text())
    manifest = json.loads((firmware / 'manifest.json').read_text())
    expected_dataset = json.loads((ROOT / 'vectors/manifest.json').read_text())
    image_sha = hashlib.sha256((firmware / 'pow-rp2040.bin').read_bytes()).hexdigest()
    if device['firmware_sha'] != image_sha or image_sha != manifest['firmware_sha']:
        raise ValueError('running firmware differs from the verified flash artifact')
    if device['dataset_sha'] != expected_dataset['sha256']:
        raise ValueError('device used a different input corpus')
    capability(device, manifest)
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
    if any(int(r['timer_hz']) != device['clock_hz'] for r in trials):
        raise ValueError('timer frequency differs from audited clock configuration')
    check_intervals(trials, device)
    try:
        references(capture)
    except subprocess.CalledProcessError as error:
        if (not record_accuracy_failure or error.returncode != 1
                or error.cmd[0] != str(capture / 'mpfr-check')):
            raise
        stats = list(csv.DictReader((capture / 'accuracy.csv').read_text().splitlines()))
        if len(stats) != 16 or not any(failed(row) for row in stats):
            raise
    return device, manifest


def failed(row):
    return int(row['class_mismatch']) or int(row['signed_zero_mismatch']) or float(row['accuracy_max_ulp']) > 1


def metadata(device, firmware):
    sections = firmware['sections']
    compiler = firmware['compiler_version'].splitlines()
    revision = firmware['source_sha']
    files = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', revision,
                                     'libm/src/math/pow'], cwd=ROOT.parent, text=True).splitlines()
    files = sorted(p for p in files if p.endswith('.rs')) + ['libm/src/math/pow.rs']
    candidate_source = b''.join(subprocess.check_output(['git', 'show', f'{revision}:{p}'], cwd=ROOT.parent) for p in files)
    return dict(
        board=firmware['board'], soc=firmware['soc'], core='Cortex-M0+',
        target_triple=firmware['target_triple'], target_cpu=firmware['target_cpu'],
        target_features=json.dumps(firmware['target_features'], sort_keys=True),
        float_abi=firmware['float_abi'], fpu_mode=firmware['fpu_mode'],
        libc_or_runtime=firmware['hal_revision'] + '; disable-intrinsics; Rust compiler_builtins FP32/64; no libc',
        compiler_backend=next(s for s in compiler if s.startswith('LLVM version:')),
        compiler_version=compiler[0], run_id=device['run_id'] + '-' + device['payload_sha256'][:16], device_id=device['device_id'],
        architecture='Arm', source_sha=revision, firmware_sha=firmware['firmware_sha'],
        dataset_sha=device['dataset_sha'], build_flags=firmware['build_flags'],
        clock_hz=device['clock_hz'], timer='core_cycles', timer_hz=device['clock_hz'], counter_bits=24,
        interrupt_configuration='PRIMASK=1; SysTick IRQ disabled; USB polled outside timed batches',
        memory_configuration=f"XIP Flash code/tables; generic 03h SPI clk_sys/4; JEDEC={device['flash_jedec']:#x}; XIP CTRL={device['xip_ctrl']:#x}; striped SRAM stack; USB SOF clock check={device['sof_clock_hz']} Hz; core 0 only",
        text_bytes=sections['.text'], rodata_bytes=sections['.rodata'],
        ram_bytes=sections['.data'] + sections['.bss'], data_bytes=sections['.data'], bss_bytes=sections['.bss'],
        size_scope='whole dual-algorithm firmware; static RAM only; 128 KiB payload on unmeasured stack',
        algorithm_revisions={'Baseline': 'git:6bc104a50f83cb205790c61c5d33508046f5fad3',
                             'Candidate': 'sha256:' + hashlib.sha256(candidate_source).hexdigest()},
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('capture', type=Path)
    parser.add_argument('--firmware', type=Path, required=True)
    parser.add_argument('--record-accuracy-failure', action='store_true',
                        help='retain timing evidence with accuracy FAIL; never waive image/capability checks')
    args = parser.parse_args()
    device, firmware = accept(args.capture, args.firmware, args.record_accuracy_failure)
    rows = summarize(list(csv.DictReader((args.capture / 'timing.csv').read_text().splitlines())), metadata(device, firmware))
    accuracy = {(r['test_distribution'], r['implementation']): r for r in csv.DictReader((args.capture / 'accuracy.csv').read_text().splitlines())}
    status = 'FAIL' if any(failed(r) for r in accuracy.values()) else 'PASS'
    for row in rows:
        row['accuracy_max_ulp'] = accuracy[row['test_distribution'], row['implementation']]['accuracy_max_ulp']
        row['accuracy_status'] = status
        if status == 'FAIL':
            row['reason'] = 'Runtime fails full-corpus MPFR acceptance; timing is diagnostic, not a qualified optimization'
    write_csv(args.capture / 'hardware.csv', rows)
    print(f'Recorded {len(rows)} verified hardware timings; full-corpus MPFR accuracy {status}')


if __name__ == '__main__':
    main()
