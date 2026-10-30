"""Reject incomplete binary records and any unaccounted trailing output bytes."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from validate import ROOT


def check(output):
    artifacts = output / 'artifacts'
    records = (artifacts / 'native-outputs.bin').read_bytes()
    labels = (artifacts / 'domains.txt').read_text().splitlines(keepends=True)
    results = []
    with tempfile.TemporaryDirectory(prefix='libm-exp-records-') as temporary:
        root = Path(temporary)
        for name, data, selected_labels in [('truncated-record', records[:-1], labels[:-1]),
                                             ('trailing-byte', records + b'\x01', labels)]:
            path, domains = root / 'records.bin', root / 'domains.txt'
            path.write_bytes(data)
            domains.write_text(''.join(selected_labels))
            result = subprocess.run([str(artifacts / 'mpfr-check'), str(path), str(domains)],
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode != 6:
                raise ValueError(f'{name}: corrupt records were not rejected: {result.returncode}')
            results.append(dict(case=name, expected_exit=6, observed_exit=result.returncode, status='PASS'))
    (output / 'record-validation.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results')
    check(parser.parse_args().output.resolve())
