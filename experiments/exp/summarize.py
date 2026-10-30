"""Summarize the 15 observed rounds without treating the feedback kernel as pure latency."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path
import statistics


def summarize(paths, destination):
    groups = defaultdict(list)
    for path in paths:
        for row in csv.DictReader(Path(path).open()):
            key = tuple(row[field] for field in ['runtime', 'function', 'implementation', 'domain', 'mode'])
            groups[key].append(row)
    summaries = []
    for key, group in groups.items():
        if len(group) != 15 or sorted(int(row['round']) for row in group) != list(range(15)):
            raise ValueError(f'incomplete or duplicated rounds for {key}')
        checksums = sorted({row['checksum'] for row in group})
        if len(checksums) != 1:
            raise ValueError(f'non-deterministic checksum for {key}: {checksums}')
        values = sorted(float(row['ns_per_op']) for row in group)
        quantiles = statistics.quantiles(values, n=10, method='inclusive')
        summaries.append(dict(zip(['runtime', 'function', 'implementation', 'domain', 'mode'], key)) |
                         dict(rounds=15, median_ns=statistics.median(values), p10_ns=quantiles[0],
                              p90_ns=quantiles[8], checksum=checksums[0],
                              calls_per_round=group[0]['calls']))
    for row in summaries:
        baseline = next(item for item in summaries if all(item[k] == row[k] for k in
                        ['runtime', 'function', 'domain', 'mode']) and item['implementation'] in ['libm_base', 'std_rebuilt_base'])
        row['speedup_vs_baseline'] = baseline['median_ns'] / row['median_ns']
    with destination.open('w') as output:
        writer = csv.DictWriter(output, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('inputs', nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    summarize(arguments.inputs, arguments.output)
