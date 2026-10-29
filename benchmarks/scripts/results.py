"""Validate full hardware identities and compute paired, within-run speedups."""
import csv
import math
import statistics
from collections import defaultdict

CAPABILITIES = {'software_fp32_fp64', 'hardware_fp32_software_fp64',
                'hardware_fp64', 'dcp_assisted_fp64'}
STATUSES = {'PASS', 'FAIL', 'UNSUPPORTED', 'NOT_TESTED', 'BLOCKED'}
IDENTITY = [
    'board', 'soc', 'core', 'target_triple', 'target_cpu', 'target_features',
    'float_abi', 'fpu_mode', 'libc_or_runtime', 'compiler_backend',
    'compiler_version', 'algorithm_revision',
]
CONTEXT = [
    'run_id', 'device_id', 'architecture', 'source_sha', 'firmware_sha',
    'dataset_sha', 'build_flags', 'clock_hz', 'timer', 'timer_hz',
    'counter_bits', 'interrupt_configuration', 'memory_configuration',
]
FIELDS = IDENTITY + CONTEXT + [
    'implementation', 'test_distribution', 'mode', 'rounds', 'iterations',
    'cycles_per_op', 'ns_per_op', 'speedup', 'p10_ns', 'p90_ns',
    'p10_speedup', 'p90_speedup', 'text_bytes', 'rodata_bytes', 'ram_bytes',
    'data_bytes', 'bss_bytes', 'stack_bytes', 'size_scope', 'accuracy_max_ulp',
    'accuracy_status', 'measurement_status', 'checksums', 'reason',
]


def validate(row):
    missing = set(FIELDS) - row.keys()
    if missing:
        raise ValueError(f'missing fields: {sorted(missing)}')
    if row['measurement_status'] not in STATUSES or row['accuracy_status'] not in STATUSES:
        raise ValueError('unknown measurement or accuracy status')
    if row['measurement_status'] != 'PASS':
        if not row['reason']:
            raise ValueError('unmeasured or failed rows need an explicit reason')
        return
    for name in IDENTITY + ['run_id', 'dataset_sha', 'test_distribution', 'mode', 'timer']:
        if row[name] is None or row[name] == '':
            raise ValueError(f'cannot report a measurement without {name}')
    if row['fpu_mode'] not in CAPABILITIES:
        raise ValueError('unknown floating-point capability class')
    if row['cycles_per_op'] in ('', None) and row['ns_per_op'] in ('', None):
        raise ValueError('a timed result requires cycles or nanoseconds')
    for name in ['cycles_per_op', 'ns_per_op', 'speedup', 'text_bytes', 'rodata_bytes',
                 'ram_bytes', 'data_bytes', 'bss_bytes', 'stack_bytes', 'accuracy_max_ulp']:
        if row[name] not in ('', None):
            value = float(row[name])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'invalid {name}')
    if row['accuracy_status'] == 'PASS' and row['accuracy_max_ulp'] in ('', None):
        raise ValueError('accuracy PASS requires an observed MPFR error')


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    lower = int(position)
    return values[lower] + (values[min(lower + 1, len(values) - 1)] - values[lower]) * (position - lower)


def summarize(raw, metadata):
    groups = defaultdict(dict)
    for row in raw:
        key = (row['test_distribution'], row['mode'], row['round'])
        if row['implementation'] in groups[key]:
            raise ValueError(f'duplicate trial: {key}')
        if int(row['ticks']) <= 0 or int(row['calls']) <= 0 or int(row['timer_hz']) <= 0:
            raise ValueError('invalid timer interval or operation count')
        groups[key][row['implementation']] = row
    aggregates = defaultdict(list)
    for (domain, mode, round_id), pair in groups.items():
        if set(pair) != {'Baseline', 'Candidate'}:
            raise ValueError('unpaired baseline/candidate trial')
        if pair['Baseline']['calls'] != pair['Candidate']['calls']:
            raise ValueError('paired trials must have identical operation counts')
        ns = {key: int(row['ticks']) * 1e9 / int(row['timer_hz']) / int(row['calls']) for key, row in pair.items()}
        for key, row in pair.items():
            aggregates[domain, mode, key].append((ns[key], ns['Baseline'] / ns[key], row))
    results = []
    for (domain, mode, implementation), samples in aggregates.items():
        if len(samples) < 15:
            raise ValueError('at least 15 paired rounds are required')
        times, ratios = [s[0] for s in samples], [s[1] for s in samples]
        row = dict.fromkeys(FIELDS, '') | metadata | dict(
            implementation=implementation, test_distribution=domain, mode=mode,
            algorithm_revision=metadata['algorithm_revisions'][implementation],
            rounds=len(samples), iterations=samples[0][2]['calls'],
            ns_per_op=statistics.median(times), speedup=statistics.median(ratios),
            p10_ns=percentile(times, .1), p90_ns=percentile(times, .9),
            p10_speedup=percentile(ratios, .1), p90_speedup=percentile(ratios, .9),
            checksums=';'.join(sorted({s[2]['checksum'] for s in samples})),
            measurement_status='PASS', accuracy_status='NOT_TESTED',
        )
        if metadata.get('timer') == 'core_cycles':
            row['cycles_per_op'] = statistics.median(int(s[2]['ticks']) / int(s[2]['calls']) for s in samples)
        row = {k: row[k] for k in FIELDS}
        validate(row)
        results.append(row)
    return results


def write_csv(path, rows):
    with open(path, 'w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            validate(row)
            writer.writerow(row)
