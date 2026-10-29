"""Run the archived 151,083-pair random/boundary corpus through the actual host binary."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2] / 'experiments/pow'


def validate(directory, binary, references):
    manifest = json.loads((ROOT / 'results/artifact-manifest.json').read_text())
    data = {}
    for name in ['inputs.bin', 'accuracy-domains.txt']:
        path = 'results/raw/' + name + '.gz'
        compressed = (ROOT / path).read_bytes()
        if hashlib.sha256(compressed).hexdigest() != manifest[path]['sha256']:
            raise ValueError('archived precision corpus has changed: ' + path)
        data[name] = gzip.decompress(compressed)
    inputs = data['inputs.bin']
    domains = data['accuracy-domains.txt'].decode().splitlines()
    if len(inputs) != 151083 * 16 or len(domains) != 151083:
        raise ValueError('unexpected precision corpus extent')
    destination = directory / 'large-accuracy'
    destination.mkdir(exist_ok=False)
    source = destination / 'inputs.bin'
    source.write_bytes(inputs)
    raw = destination / 'unlabelled.csv'
    with raw.open('w') as stream:
        subprocess.run([str(binary), 'accuracy-file', str(source)], stdout=stream, check=True)
    with raw.open() as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != len(domains):
        raise ValueError('host returned an incomplete precision stream')
    pairs = b''.join(struct.pack('<QQ', int(r['x_bits'], 16), int(r['y_bits'], 16)) for r in rows)
    if pairs != inputs or [int(r['index']) for r in rows] != list(range(len(rows))):
        raise ValueError('host substituted or reordered precision inputs')
    for domain, row in zip(domains, rows):
        row['test_distribution'] = domain
    bits = destination / 'accuracy-bits.csv'
    with bits.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    references(destination)
    evidence = dict(cases=len(rows), input_sha256=hashlib.sha256(inputs).hexdigest(),
                    binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
                    output_sha256=hashlib.sha256(bits.read_bytes()).hexdigest(),
                    input_source='experiments/pow/results/raw/inputs.bin.gz',
                    domain_source='experiments/pow/results/raw/accuracy-domains.txt.gz',
                    acceptance='PASS; MPFR 256-bit, round-to-nearest, error <= 1 ULP, classification and signed zero')
    (destination / 'manifest.json').write_text(json.dumps(evidence, indent=2) + '\n')
    (destination / 'accuracy-bits.csv.gz').write_bytes(gzip.compress(bits.read_bytes(), mtime=0))
    for path in [source, raw, bits]:
        path.unlink()
