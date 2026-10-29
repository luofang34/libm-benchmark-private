"""Summarize every measured round without dropping slow samples."""
from pathlib import Path
from collections import defaultdict
import csv,statistics
root=Path(__file__).resolve().parent
groups=defaultdict(list)
for path in ['native.csv','wasm.csv','wasm-rebuilt-base.csv','wasm-rebuilt-patch.csv']:
    for row in csv.DictReader((root/'results/raw'/path).open()):
        groups[tuple(row[k] for k in ['runtime','implementation','domain','mode'])].append(row)
rows=[]
for key,group in groups.items():
    values=sorted(float(x['ns_per_op']) for x in group)
    def percentile(q):
        i=(len(values)-1)*q;lo=int(i);return values[lo]+(values[min(lo+1,len(values)-1)]-values[lo])*(i-lo)
    assert len(values)==15,(key,len(values))
    rows.append(dict(zip(['runtime','implementation','domain','mode'],key))|dict(function='pow_f64',rounds=len(values),median_ns=statistics.median(values),p10_ns=percentile(.1),p90_ns=percentile(.9),checksums=';'.join(sorted(set(x['checksum'] for x in group))),calls_per_round=group[0]['calls']))
with (root/'performance.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
for row in rows:
    if row['domain']=='positive':print(row['runtime'],row['implementation'],row['mode'],round(row['median_ns'],3))
