"""Collect accepted runs without averaging unlike hardware or accuracy populations."""
import csv
from pathlib import Path

from results import write_csv

ROOT = Path(__file__).resolve().parents[1] / 'results'


def main():
    hardware, hosted, accuracy = [], [], []
    for capture in sorted((ROOT / 'raw-logs').iterdir()):
        for name, destination in [('hardware.csv', hardware), ('hosted.csv', hosted)]:
            path = capture / name
            if not path.exists():
                continue
            with path.open() as source:
                rows = list(csv.DictReader(source))
            destination.extend(rows)
            identity = {k: rows[0][k] for k in ['board', 'device_id', 'target_cpu', 'fpu_mode', 'firmware_sha', 'run_id']}
            with (capture / 'accuracy.csv').open() as source:
                accuracy.extend(identity | row for row in csv.DictReader(source))
    write_csv(ROOT / 'hardware.csv', hardware)
    write_csv(ROOT / 'hosted.csv', hosted)
    if not accuracy:
        raise ValueError('no validated accuracy records')
    with (ROOT / 'accuracy.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=accuracy[0].keys())
        writer.writeheader()
        writer.writerows(accuracy)
    print(f'{len(hardware)} hardware rows; {len(hosted)} hosted rows; {len(accuracy)} accuracy rows')


if __name__ == '__main__':
    main()
