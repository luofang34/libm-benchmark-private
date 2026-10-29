"""Build and inspect ESP32-C6 images, including actual ROM arithmetic call targets."""
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
BOARD = ROOT / 'boards/esp32c6'
TARGET = 'riscv32imac-unknown-none-elf'
FLAGS = '-C target-cpu=generic-rv32 -C link-arg=-Tlinkall.x'


def app_image(merged):
    image = merged[0x10000:]
    if (len(image) < 24 or image[0] != 0xe9 or not 1 <= image[1] <= 16
            or image[12:14] != b'\x0d\x00' or image[23] != 1):
        raise ValueError('wrong ESP32-C6 image header')
    offset, checksum = 24, 0xef
    segments = []
    for _ in range(image[1]):
        if offset + 8 > len(image):
            raise ValueError('truncated load segment header')
        address, length = struct.unpack_from('<II', image, offset)
        offset += 8
        segment = image[offset:offset + length]
        if len(segment) != length:
            raise ValueError('truncated load segment')
        for byte in segment:
            checksum ^= byte
        segments.append(dict(address=hex(address), bytes=length))
        offset += length
    end = (offset + 16) // 16 * 16
    if len(image) != end + 32 or len(image) > 0x100000:
        raise ValueError('unexpected application extent')
    if image[end - 1] != checksum or hashlib.sha256(image[:end]).digest() != image[end:end + 32]:
        raise ValueError('ESP image checksum or appended SHA mismatch')
    return image, segments


def call_targets(assembly):
    instructions = [(int(a, 16), int(word, 16)) for a, word in
                    re.findall(r'^([0-9a-f]+):\s+([0-9a-f]{8})\s', assembly, re.M)]
    targets = []
    for (pc, upper), (next_pc, jump) in zip(instructions, instructions[1:]):
        if (next_pc == pc + 4 and upper & 0x7f == 0x17 and jump & 0x707f == 0x67
                and (upper >> 7) & 31 == (jump >> 15) & 31):
            immediate = (jump >> 20) - (4096 if jump >> 31 else 0)
            targets.append((pc + (upper & 0xfffff000) + immediate) & 0xfffffffe)
    return targets


def audit(reports, implementation):
    assembly, symbols = reports['assembly'], reports['symbols']
    if re.search(r'\bf(?:add|mul|div|sub|sqrt|madd)\.[sd]\b', assembly):
        raise ValueError('hardware floating-point instruction on ESP32-C6')
    for prefix in [implementation.lower()] if implementation else ['baseline', 'candidate']:
        if not re.search(r'\b(?:jal|jalr)\s+.*' + prefix + '_pow', assembly):
            raise ValueError('actual pow call missing: ' + prefix)
    if implementation and ('candidate_pow' if implementation == 'Baseline' else 'baseline_pow') in symbols:
        raise ValueError('both algorithms in single-algorithm fixture')
    targets = call_targets(assembly)
    helpers = {'__adddf3': 0x400009f4, '__muldf3': 0x40000a64, '__divdf3': 0x400008d0}
    if not implementation:
        helpers |= {'__addsf3': 0x400009f8, '__mulsf3': 0x40000a68, '__divsf3': 0x400008dc}
    for name, address in helpers.items():
        if not re.search(f'^{address:08x}\\s+00000000\\s+[aA]\\s+{name}$', symbols, re.M) or address not in targets:
            raise ValueError('expected ROM floating-point call missing: ' + name)
    for address, name in re.findall(r'^([0-9a-f]+)\s+[0-9a-f]+\s+\w\s+(\w+)$', symbols, re.M):
        if name in ['fma', 'fmaf', 'pow', 'exp', 'log', '__fmadf3'] and int(address, 16) in targets:
            raise ValueError('unintended math libcall: ' + name)
    return {name: dict(address=hex(address), calls=targets.count(address)) for name, address in helpers.items()}


def build(directory, implementation=None):
    directory.mkdir(parents=True, exist_ok=True)
    name = 'pow-size' if implementation else 'pow-esp32c6'
    options = ['--manifest-path', str(BOARD / 'Cargo.toml'), '--locked', '--release', '--target', TARGET, '--bin', name]
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
    for label, command in [('assembly', [tool('objdump'), '-d', '--demangle', '--mcpu=generic-rv32']),
                           ('symbols', [tool('nm'), '-S', '--demangle']),
                           ('sections', [tool('size'), '-A']), ('attributes', [tool('readelf'), '-A'])]:
        reports[label] = subprocess.check_output(command + [str(elf)], text=True)
        (directory / (label + '.txt')).write_text(reports[label])
    if subprocess.check_output([tool('nm'), '--undefined-only', str(elf)], text=True).strip():
        raise ValueError('unresolved symbols')
    helpers = audit(reports, implementation)
    merged = directory / 'merged.bin'
    with (directory / 'image.log').open('w') as log:
        subprocess.run(['espflash', 'save-image', '--chip', 'esp32c6', '--flash-mode', 'dio', '--flash-freq', '40mhz',
                        '--flash-size', '8mb', '--merge', '--skip-padding', '--skip-update-check', str(elf), str(merged)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    image, segments = app_image(merged.read_bytes())
    (directory / 'pow-esp32c6.bin').write_bytes(image)
    sections = {key: int(value) for key, value in re.findall(r'^(\.[\w.]+)\s+(\d+)\s+\d+', reports['sections'], re.M)}
    return dict(firmware_sha=hashlib.sha256(image).hexdigest(), firmware_bytes=len(image),
                merged_sha=hashlib.sha256(merged.read_bytes()).hexdigest(), sections=sections, segments=segments, rom_helpers=helpers)


def main():
    directory = ROOT / 'firmware/esp32c6'
    result = build(directory)
    cfg = subprocess.check_output(['rustc', '--print', 'cfg', '--target', TARGET, '-C', 'target-cpu=generic-rv32'], text=True)
    manifest = result | dict(board='ESP32-C6 USB board; PCB model unreported', soc='ESP32-C6 v0.1',
        device_id='f0f5bd0c2288', flash_address='0x10000', flash_capacity=8 * 1024 * 1024,
        target_triple=TARGET, target_cpu='generic-rv32', float_abi='ilp32', fpu_mode='software_fp32_fp64',
        target_features={'cpu_defaults': 'generic-rv32', 'rustc_cfg': re.findall(r'target_feature="([^"]+)"', cfg)},
        compiler_version=subprocess.check_output(['rustc', '-vV'], text=True),
        build_flags=FLAGS + '; release opt-level=3,lto=fat,codegen-units=1,panic=abort; DIO image header 40 MHz; runtime MSPI source/clock reported by device',
        source_sha=subprocess.check_output(['git', 'rev-parse', 'experiment/pow-wasm'], text=True).strip(),
        hal_revision='5ba50dd2d21136370050dd2f7a767761e01cfeef; esp-hal 1.0.0',
        rom_revision='160b10794227eb84805b8676fe188c1110801e9d; esp-rom-sys 0.1.5; esp32c6.rom.rvfp.ld',
        clock_source='ROM detected 40 MHz crystal; PLL 160 MHz; cycle counter cross-checked against SYSTIMER within 0.5%',
        scope='dual-algorithm app image; bootloader/partition table separate; static RAM excludes stack', preflight='PASS')
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
