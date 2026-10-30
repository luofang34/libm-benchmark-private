"""Time complete native Rust loops; ctypes is outside the timed region."""
import argparse
import csv
import ctypes
import sys

DOMAINS = ['normal', 'near_zero', 'subnormal_input', 'subnormal_output', 'range_edge', 'special']
FIELDS = ['runtime', 'function', 'implementation', 'domain', 'mode', 'round',
          'ns_per_op', 'checksum', 'calls']


class Measurement(ctypes.Structure):
    _fields_ = [('ns', ctypes.c_double), ('checksum', ctypes.c_uint64), ('calls', ctypes.c_uint64)]


def load(path):
    library = ctypes.CDLL(str(path))
    library.run_bench.argtypes = [ctypes.c_uint32] * 5
    library.run_bench.restype = Measurement
    library.unary_bits.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint64]
    library.unary_bits.restype = ctypes.c_uint64
    return library


def benchmark(base, candidate, repeats):
    libraries = [load(base), load(candidate)]
    choices = [(0, 0, 'libm_base'), (1, 0, 'libm_candidate'), (0, 1, 'std_system'), (0, 2, 'control')]
    writer = csv.writer(sys.stdout)
    writer.writerow(FIELDS)
    for function, name in enumerate(['exp', 'exp2']):
        for domain, distribution in enumerate(DOMAINS):
            for mode, mode_name in enumerate(['throughput', 'dependency_kernel']):
                for iteration in range(20):
                    for offset in range(len(choices)):
                        variant, kind, implementation = choices[(offset + iteration) % len(choices)]
                        result = libraries[variant].run_bench(function, kind, mode, domain, repeats)
                        if result.calls != 16384 * repeats:
                            raise ValueError('incomplete Rust timing loop')
                        if iteration >= 5:
                            writer.writerow(['native', name, implementation, distribution, mode_name,
                                             iteration - 5, result.ns / result.calls,
                                             f'{result.checksum:016x}', result.calls])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('base')
    parser.add_argument('candidate')
    parser.add_argument('--repeats', type=int, default=32)
    arguments = parser.parse_args()
    benchmark(arguments.base, arguments.candidate, arguments.repeats)
