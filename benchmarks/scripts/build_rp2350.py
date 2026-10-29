"""Build and audit separate RP2350 Arm, Hazard3 and DCP measurement images."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

from build_f411 import tool

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / 'boards/rp2350'
MODES = {
    'arm': ('thumbv8m.main-none-eabihf', 'cortex-m33', 'aapcs-vfp', 'hardware_fp32_software_fp64'),
    'riscv': ('riscv32imac-unknown-none-elf', 'generic-rv32', 'ilp32', 'software_fp32_fp64'),
    'dcp': ('thumbv8m.main-none-eabihf', 'cortex-m33', 'aapcs-vfp', 'dcp_assisted_fp64'),
}


def flags(mode):
    script = 'rp235x_riscv.x' if mode == 'riscv' else 'link.x'
    return f'-C target-cpu={MODES[mode][1]} -C link-arg=--nmagic -C link-arg=-T{script} -C link-arg=-Timage-end.x'


def build(mode, directory, implementation=None):
    directory.mkdir(parents=True, exist_ok=True)
    features = ['dcp'] if mode == 'dcp' else []
    if implementation:
        features += ['size-candidate' if implementation == 'Candidate' else 'size-fixture']
    name = 'pow-size' if implementation else 'pow-rp2350'
    options = ['--manifest-path', str(BOARD / 'Cargo.toml'), '--locked', '--release',
               '--target', MODES[mode][0], '--bin', name]
    if features:
        options += ['--features', ','.join(features)]
    env = os.environ.copy() | {'RUSTFLAGS': flags(mode)}
    for command in ['clippy', 'build']:
        with (directory / (command + '.log')).open('w') as log:
            subprocess.run(['cargo', command, *options, *(['--', '-D', 'warnings'] if command == 'clippy' else [])],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    source = BOARD / 'target' / MODES[mode][0] / 'release' / name
    elf = directory / (name + '.elf')
    shutil.copyfile(source, elf)
    reports = {}
    for label, command in [('assembly', [tool('objdump'), '-d', '--demangle', '--mcpu=' + MODES[mode][1]]),
                           ('symbols', [tool('nm'), '-S', '--demangle']),
                           ('sections', [tool('size'), '-A']), ('attributes', [tool('readelf'), '-A'])]:
        reports[label] = subprocess.check_output(command + [str(elf)], text=True)
        (directory / (label + '.txt')).write_text(reports[label])
    if subprocess.check_output([tool('nm'), '--undefined-only', str(elf)], text=True).strip():
        raise ValueError('unresolved symbols')
    selected = [implementation.lower()] if implementation else ['baseline', 'candidate']
    for prefix in selected:
        if not re.search(r'\b(?:bl|jal|jalr)\s+.*' + prefix + '_pow', reports['assembly']):
            raise ValueError('actual pow call missing: ' + prefix)
    if implementation:
        unwanted = 'candidate_pow' if implementation == 'Baseline' else 'baseline_pow'
        if unwanted in reports['symbols']:
            raise ValueError('both algorithms are linked in a single-algorithm fixture')
    audit_arithmetic(mode, reports, implementation is None)
    binary = directory / (name + '.bin')
    subprocess.run([tool('objcopy'), '-O', 'binary', str(elf), str(binary)], check=True)
    data = binary.read_bytes()
    match = re.search(r'^([0-9a-f]+)\s+(?:[0-9a-f]+\s+)?\w\s+__flash_image_end$', reports['symbols'], re.M)
    if not match:
        raise ValueError('missing Flash hash boundary')
    size = int(match[1], 16) - 0x10000000
    if not len(data) <= size <= 4 * 1024 * 1024:
        raise ValueError('invalid Flash image bounds')
    data += b'\xff' * (size - len(data))
    binary.write_bytes(data)
    if mode != 'riscv':
        stack, reset = struct.unpack('<II', data[:8])
        if not (0x20000000 < stack <= 0x20080000 and stack % 8 == 0 and reset & 1 and
                0x10000000 <= reset - 1 < 0x10000000 + size):
            raise ValueError('invalid Arm reset vector or stack')
    if not implementation:
        info = subprocess.check_output(['picotool', 'info', '-a', str(binary), '-t', 'bin'], text=True)
        (directory / 'image-info.log').write_text(info)
        expected = 'RISC-V' if mode == 'riscv' else 'ARM Secure'
        if expected not in info or 'RP2350' not in info:
            raise ValueError('ROM image definition has the wrong architecture/security type')
    sections = {key: int(value) for key, value in re.findall(r'^(\.[\w.]+)\s+(\d+)\s+\d+', reports['sections'], re.M)}
    return dict(firmware_sha=hashlib.sha256(data).hexdigest(), firmware_bytes=len(data), sections=sections)


def audit_arithmetic(mode, reports, probe):
    assembly, symbols = reports['assembly'], reports['symbols']
    if re.search(r'\b(?:fma|pow|__fmadf3)\s*$', symbols, re.M):
        raise ValueError('unintended math libcall')
    if mode == 'riscv':
        if re.search(r'\bf(?:add|mul|div|sub|sqrt|madd)\.[sd]\b', assembly):
            raise ValueError('hardware floating-point instruction on Hazard3')
        helpers = ['__adddf3', '__muldf3'] + (['__addsf3', '__mulsf3'] if probe else [])
    else:
        if re.search(r'v(?:add|mul|div|sub|sqrt|fma)\.f64', assembly):
            raise ValueError('hardware FP64 instruction on M33')
        if probe and not re.search(r'v(?:add|mul|div)\.f32', assembly):
            raise ValueError('hardware FP32 probe missing')
        if mode == 'dcp':
            if not re.search(r'\b(?:mcrr|mrrc|cdp)\s+p4', assembly):
                raise ValueError('DCP instructions missing')
            helpers = ['_aapcs_dcp_add', '_aapcs_dcp_mul']
        else:
            if '_aapcs_dcp_' in symbols or re.search(r'\b(?:mcrr|mrrc|cdp)\s+p4', assembly):
                raise ValueError('DCP arithmetic in software FP64 build')
            helpers = ['__aeabi_dadd', '__aeabi_dmul']
    for helper in helpers:
        if helper not in symbols or not re.search(r'\b(?:bl|b\.w|jal|jalr|j)\s+.*' + helper, assembly):
            raise ValueError('actual floating-point helper call missing: ' + helper)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=MODES)
    args = parser.parse_args()
    directory = ROOT / 'firmware' / ('rp2350-' + args.mode)
    result = build(args.mode, directory)
    triple, cpu, abi, fpu = MODES[args.mode]
    cfg = subprocess.check_output(['rustc', '--print', 'cfg', '--target', triple, '-C', 'target-cpu=' + cpu], text=True)
    manifest = result | dict(board='RP2350 USB BOOTSEL board; PCB model unreported', soc='RP2350 A2', mode=args.mode,
        device_id='e4552bccfbae6dad', flash_address='0x10000000', flash_capacity=4 * 1024 * 1024,
        target_triple=triple, target_cpu=cpu, float_abi=abi, fpu_mode=fpu,
        target_features={'cpu_defaults': cpu, 'rustc_cfg': re.findall(r'target_feature="([^"]+)"', cfg)},
        compiler_version=subprocess.check_output(['rustc', '-vV'], text=True),
        build_flags=flags(args.mode) + '; release opt-level=3,lto=fat,codegen-units=1,panic=abort; features=' + ('dcp' if args.mode == 'dcp' else 'none'),
        source_sha=subprocess.check_output(['git', 'rev-parse', 'experiment/pow-wasm'], text=True).strip(),
        hal_revision='fa430d279b8f185769fe2e5e9aca0e57290acd1f; rp235x-hal 0.4.0',
        clock_source='12 MHz XOSC assumption; PLL 150 MHz; checked against USB SOF within 0.5%',
        scope='dual-algorithm firmware; static RAM excludes 128 KiB retained payload and other stack frames', preflight='PASS')
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
