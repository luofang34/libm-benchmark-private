"""Generate deterministic unary cases, including exact reduction-boundary neighbors."""
import argparse
import json
import math
from pathlib import Path
import random
import struct


def bits(value):
    return struct.unpack('<Q', struct.pack('<d', value))[0]


def value(word):
    return struct.unpack('<d', struct.pack('<Q', word & ((1 << 64) - 1)))[0]


def corpus(destination):
    random_source = random.Random(20261030)
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for function in range(2):
        factor = math.log(2) if function == 0 else 1.0
        for _ in range(20000):
            records.extend([
                (function, 'normal', random_source.uniform(-16, 16) * factor),
                (function, 'near_zero', random_source.uniform(-1e-8, 1e-8)),
                (function, 'subnormal_input', value(random_source.getrandbits(52) |
                                                   (random_source.randrange(2) << 63))),
                (function, 'subnormal_output', random_source.uniform(-1076, -1021) * factor),
                (function, 'range_edge', (random_source.choice([-1075, -1074, -1022, 1024]) +
                                         random_source.uniform(-1e-8, 1e-8)) * factor),
                (function, 'random_bits', value(random_source.getrandbits(64))),
                (function, 'wide_finite', random_source.uniform(-1100, 1100) * factor),
            ])
        # Include all table indices, several exponents, and adjacent doubles on
        # both sides of the half-step reduction choice.
        for exponent in [-1075, -1074, -1022, -1, 0, 1, 512, 1023, 1024]:
            for index in range(128):
                center = (exponent + (index + 0.5) / 128) * factor
                for step in range(-2, 3):
                    records.append((function, 'table_boundary', value(bits(center) + step)))
        for center in [0.0, -0.0, -3.0 / 256.0, math.ldexp(1, -54), -math.ldexp(1, -54)]:
            for step in range(-32, 33):
                adjacent = center
                for _ in range(abs(step)):
                    adjacent = math.nextafter(adjacent, math.inf if step > 0 else -math.inf)
                records.append((function, 'adversarial_zero', adjacent))
        special = [0.0, -0.0, math.inf, -math.inf, math.nan, value(0x7ff0000000000001),
                   value(0xfff0000000000001), value(1), -value(1), value(0x0010000000000000),
                   value(0x7fefffffffffffff), -value(0x7fefffffffffffff)]
        records.extend((function, 'special', x) for x in special)
    (destination / 'inputs.bin').write_bytes(b''.join(struct.pack('<QQ', f, bits(x)) for f, _, x in records))
    (destination / 'domains.txt').write_text(''.join(f'{domain}\n' for _, domain, _ in records))
    (destination / 'corpus.json').write_text(json.dumps(dict(seed=20261030, cases=len(records),
        functions=['exp', 'exp2'], per_function=len(records) // 2, byte_order='little',
        row_format='u64 function index, u64 IEEE input bits',
        includes_exp2_i0_wrap_regression=True), indent=2) + '\n')
    return len(records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    print(corpus(parser.parse_args().output))
