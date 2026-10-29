"""Read USB CDC and probe inventories without guessing pins or resetting a device."""
import glob
import json
import platform
import shutil
import subprocess


def snapshot():
    ports = sorted(set(glob.glob('/dev/cu.usb*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')))
    result = {'serial_ports': ports, 'measurement_status': 'NOT_TESTED'}
    commands = []
    if platform.system() == 'Darwin':
        commands += [('usb', ['ioreg', '-r', '-c', 'IOUSBHostDevice', '-l', '-w', '0']),
                     ('cdc', ['ioreg', '-r', '-c', 'IOSerialBSDClient', '-l'])]
    elif shutil.which('lsusb'):
        commands.append(('usb', ['lsusb']))
    if shutil.which('probe-rs'):
        commands.append(('debug_probes', ['probe-rs', 'list']))
    for name, command in commands:
        process = subprocess.run(command, capture_output=True, text=True, timeout=30)
        result[name] = {'exit_code': process.returncode, 'output': process.stdout, 'stderr': process.stderr}
    return result


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
