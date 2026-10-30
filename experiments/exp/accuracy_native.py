"""Evaluate native exports bit-for-bit, outside performance timing."""
import argparse
from pathlib import Path
import struct
from bench_native import load


def evaluate(inputs, base, candidate, output):
    libraries = [load(base), load(candidate)]
    rows = []
    for function, word in struct.iter_unpack('<QQ', inputs.read_bytes()):
        results = [libraries[0].unary_bits(function, 0, word),
                   libraries[1].unary_bits(function, 0, word),
                   libraries[0].unary_bits(function, 1, word)]
        rows.append(struct.pack('<QQQQQ', function, word, *results))
    output.write_bytes(b''.join(rows))
    print(f'Evaluated {len(rows)} native cases through numeric Rust exports.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('inputs', type=Path)
    parser.add_argument('base', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    evaluate(args.inputs, args.base, args.candidate, args.output)
