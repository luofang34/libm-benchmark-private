"""Build and audit the USB FS F411 firmware before it can be offered for flashing."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / 'boards/stm32f411'
DEST = ROOT / 'firmware/f411'
FLAGS = '-C target-cpu=cortex-m4 -C link-arg=-Tlink.x -C link-arg=-Timage-end.x'


def tool(name):
    command = shutil.which('llvm-' + name)
    fallback = Path('/opt/homebrew/opt/llvm/bin') / ('llvm-' + name)
    if command:
        return command
    if fallback.exists():
        return str(fallback)
    raise FileNotFoundError('LLVM tool required: ' + name)


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy() | {'RUSTFLAGS': FLAGS}
    for name, command in [('clippy', ['cargo', 'clippy']), ('build', ['cargo', 'build'])]:
        command += ['--manifest-path', str(BOARD / 'Cargo.toml'), '--locked', '--release', '--target', 'thumbv7em-none-eabihf']
        if name == 'clippy':
            command += ['--', '-D', 'warnings']
        with (DEST / (name + '.log')).open('w') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    elf = BOARD / 'target/thumbv7em-none-eabihf/release/pow-f411'
    shutil.copyfile(elf, DEST / 'pow-f411.elf')
    reports = {}
    for name, command in [('assembly', [tool('objdump'), '-d', '--demangle', '--mcpu=cortex-m4']),
                          ('symbols', [tool('nm'), '-S', '--demangle']),
                          ('sections', [tool('size'), '-A']),
                          ('attributes', [tool('readelf'), '-A'])]:
        reports[name] = subprocess.check_output(command + [str(elf)], text=True)
        (DEST / (name + '.txt')).write_text(reports[name])
    if subprocess.check_output([tool('nm'), '--undefined-only', str(elf)], text=True).strip():
        raise ValueError('firmware contains unresolved symbols')
    reset = reports['assembly'].split('<__stext>:', 1)[1].split('\n\n', 1)[0]
    preinit = reports['assembly'].split('<__pre_init>:', 1)[1].split('\n\n', 1)[0]
    if not re.search(r'\bmsr\s+msp,', reset) or '0xe000ed08' not in reset:
        raise ValueError('reset must initialize the application stack and vector table')
    if 'cpsid i' not in preinit or '0xe000e010' not in preinit:
        raise ValueError('pre-init must disable inherited interrupts and SysTick')
    for function in ['baseline_pow', 'candidate_pow']:
        if not re.search(r'\bbl\s+.*' + function, reports['assembly']):
            raise ValueError('missing actual pow call: ' + function)
    if re.search(r'v(?:add|mul|div|sub|sqrt|fma)\.f64', reports['assembly']):
        raise ValueError('unsupported hardware FP64 instruction')
    if not re.search(r'v(?:add|mul|div)\.f32', reports['assembly']):
        raise ValueError('hardware FP32 probe instructions missing')
    for helper in ['__aeabi_dadd', '__aeabi_dmul', '__aeabi_ddiv']:
        if not re.search(r'\bbl\s+.*' + helper, reports['assembly']):
            raise ValueError('missing software FP64 helper: ' + helper)
    if re.search(r'\b(?:fma|pow|__fmadf3)\s*$', reports['symbols'], re.M):
        raise ValueError('unintended math libcall in firmware')
    match = re.search(r'^([0-9a-f]+)\s+(?:[0-9a-f]+\s+)?\w\s+__flash_image_end$', reports['symbols'], re.M)
    if not match:
        raise ValueError('missing Flash-image hash boundary')
    image_size = int(match[1], 16) - 0x08000000
    image = DEST / 'pow-f411.bin'
    subprocess.run([tool('objcopy'), '-O', 'binary', str(elf), str(image)], check=True)
    data = image.read_bytes()
    if not len(data) <= image_size <= 512 * 1024:
        raise ValueError('invalid Flash image bounds')
    data += bytes([255]) * (image_size - len(data))
    image.write_bytes(data)
    stack, reset = struct.unpack('<II', data[:8])
    if not (0x20000000 < stack <= 0x20020000 and stack % 8 == 0 and reset & 1 and
            0x08000000 <= reset - 1 < 0x08000000 + image_size):
        raise ValueError('invalid reset vector or initial stack')
    sections = {name: int(size) for name, size in re.findall(r'^(\.[\w.]+)\s+(\d+)\s+\d+', reports['sections'], re.M)}
    manifest = dict(
        board='STM32F411 USB FS DFU board; PCB model unreported', soc='STM32F411',
        dfu_serial='368C358D3133', flash_address='0x08000000',
        target_triple='thumbv7em-none-eabihf', target_cpu='cortex-m4',
        requested_target_features='CPU defaults', float_abi='aapcs-vfp',
        fpu_mode='hardware_fp32_software_fp64', clock_source='HSE measured with TIM11/HSI, rounded to integer MHz; PLL nominal 48 MHz',
        firmware_sha=hashlib.sha256(data).hexdigest(), firmware_bytes=len(data),
        source_sha=subprocess.check_output(['git', 'rev-parse', 'experiment/pow-wasm'], text=True).strip(),
        compiler_version=subprocess.check_output(['rustc', '-vV'], text=True),
        build_flags=FLAGS, sections=sections,
        scope='dual-algorithm firmware; static RAM excludes 80 KiB stack-resident telemetry buffer',
        transport='USB FS PA11/PA12; HSE -> PLLQ at 48 MHz',
        preflight='PASS', stack_bytes=None,
    )
    (DEST / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
