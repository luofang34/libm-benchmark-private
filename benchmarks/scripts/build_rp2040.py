"""Build RP2040 compiler-software-FP firmware and audit its boot image and arithmetic."""
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
BOARD = ROOT / 'boards/rp2040'
TARGET = 'thumbv6m-none-eabi'
FLAGS = '-C target-cpu=cortex-m0plus -C link-arg=--nmagic -C link-arg=-Tlink.x'


def boot_crc(data):
    crc = 0xffffffff
    for byte in data:
        crc ^= byte << 24
        for _ in range(8):
            crc = ((crc << 1) ^ (0x04c11db7 if crc & 0x80000000 else 0)) & 0xffffffff
    return crc


def build(directory, implementation=None):
    directory.mkdir(parents=True, exist_ok=True)
    name = 'pow-size' if implementation else 'pow-rp2040'
    options = ['--manifest-path', str(BOARD / 'Cargo.toml'), '--locked', '--release',
               '--target', TARGET, '--bin', name]
    if implementation:
        options += ['--features', 'size-candidate' if implementation == 'Candidate' else 'size-fixture']
    env = os.environ.copy() | {'RUSTFLAGS': FLAGS}
    for command in ['clippy', 'build']:
        with (directory / (command + '.log')).open('w') as log:
            subprocess.run(['cargo', command, *options, *(['--', '-D', 'warnings'] if command == 'clippy' else [])],
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    elf = directory / (name + '.elf')
    shutil.copyfile(BOARD / 'target' / TARGET / 'release' / name, elf)
    reports = {}
    for label, command in [('assembly', [tool('objdump'), '-d', '--demangle', '--mcpu=cortex-m0plus']),
                           ('symbols', [tool('nm'), '-S', '--demangle']),
                           ('sections', [tool('size'), '-A']), ('attributes', [tool('readelf'), '-A'])]:
        reports[label] = subprocess.check_output(command + [str(elf)], text=True)
        (directory / (label + '.txt')).write_text(reports[label])
    if subprocess.check_output([tool('nm'), '--undefined-only', str(elf)], text=True).strip():
        raise ValueError('unresolved symbols')
    selected = [implementation.lower()] if implementation else ['baseline', 'candidate']
    for prefix in selected:
        if not re.search(r'\bbl\s+.*' + prefix + '_pow', reports['assembly']):
            raise ValueError('actual pow call missing: ' + prefix)
    if implementation:
        unwanted = 'candidate_pow' if implementation == 'Baseline' else 'baseline_pow'
        if unwanted in reports['symbols']:
            raise ValueError('both algorithms are linked in a single-algorithm fixture')
    audit_arithmetic(reports, implementation is None)
    binary = directory / (name + '.bin')
    subprocess.run([tool('objcopy'), '-O', 'binary', str(elf), str(binary)], check=True)
    data = binary.read_bytes()
    match = re.search(r'^([0-9a-f]+)\s+(?:[0-9a-f]+\s+)?\w\s+__flash_image_end$', reports['symbols'], re.M)
    if not match:
        raise ValueError('missing Flash hash boundary')
    size = int(match[1], 16) - 0x10000000
    if not len(data) <= size <= 128 * 1024:
        raise ValueError('invalid bounded Flash image')
    data += b'\xff' * (size - len(data))
    binary.write_bytes(data)
    if boot_crc(data[:252]) != struct.unpack('<I', data[252:256])[0]:
        raise ValueError('boot2 CRC does not match RP2040 ROM algorithm')
    stack, reset = struct.unpack('<II', data[256:264])
    if not (0x20000000 < stack <= 0x20040000 and stack % 8 == 0 and reset & 1
            and 0x10000100 <= reset - 1 < 0x10000000 + size):
        raise ValueError('invalid reset vector or stack')
    sections = {key: int(value) for key, value in re.findall(r'^(\.[\w.]+)\s+(\d+)\s+\d+', reports['sections'], re.M)}
    return dict(firmware_sha=hashlib.sha256(data).hexdigest(), firmware_bytes=len(data), sections=sections)


def audit_arithmetic(reports, probe):
    assembly, symbols = reports['assembly'], reports['symbols']
    if re.search(r'\b(?:fma|pow|__fmadf3)\s*$', symbols, re.M) or 'rp2040_hal::float' in symbols:
        raise ValueError('unintended math/ROM floating-point libcall')
    if re.search(r'v(?:add|mul|div|sub|sqrt|fma)\.f(?:32|64)', assembly):
        raise ValueError('hardware floating-point instruction on Cortex-M0+')
    helpers = ['__aeabi_dadd', '__aeabi_dmul'] + (['__aeabi_fadd', '__aeabi_fmul', '__aeabi_fdiv'] if probe else [])
    for helper in helpers:
        if helper not in symbols or not re.search(r'\bbl\s+.*' + helper, assembly):
            raise ValueError('actual software floating-point helper call missing: ' + helper)


def main():
    directory = ROOT / 'firmware/rp2040'
    result = build(directory)
    cfg = subprocess.check_output(['rustc', '--print', 'cfg', '--target', TARGET, '-C', 'target-cpu=cortex-m0plus'], text=True)
    manifest = result | dict(board='RP2040 USB BOOTSEL board; PCB model unreported', soc='RP2040 B2',
        bootsel_serial='E0C9125B0D9B', flash_address='0x10000000', linker_flash_window=128 * 1024,
        target_triple=TARGET, target_cpu='cortex-m0plus', float_abi='aapcs-soft', fpu_mode='software_fp32_fp64',
        target_features={'cpu_defaults': 'cortex-m0plus', 'rustc_cfg': re.findall(r'target_feature="([^"]+)"', cfg)},
        compiler_version=subprocess.check_output(['rustc', '-vV'], text=True),
        build_flags=FLAGS + '; release opt-level=3,lto=fat,codegen-units=1,panic=abort; HAL disable-intrinsics',
        source_sha=subprocess.check_output(['git', 'rev-parse', 'experiment/pow-wasm'], text=True).strip(),
        hal_revision='2fb63064c98edcf688694bc63dc05f57b89a71b2; rp2040-hal 0.11.0',
        clock_source='12 MHz XOSC assumption; PLL 125 MHz; checked against 50 USB SOF frames within 0.5%',
        flash_mode='rp2040-boot2 0.3.0 GENERIC_03H; one-bit SPI; clk_sys/4; XIP cache',
        scope='dual-algorithm firmware; static RAM excludes 128 KiB retained payload and other stack frames', preflight='PASS')
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
