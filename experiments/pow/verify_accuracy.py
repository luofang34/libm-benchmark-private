"""Fail the local experiment if pow's measured numerical contract regresses."""
from pathlib import Path
import csv
root=Path(__file__).resolve().parent
rows=list(csv.DictReader((root/'results/raw/accuracy.csv').open()))
for implementation in ['arm_patch','rebuilt_patch']:
    row=next(x for x in rows if x['domain']=='all' and x['implementation']==implementation)
    assert int(row['count'])==151083,row
    assert float(row['max_ulp'])<=1.0,row
    assert int(row['class_mismatch'])==0,row
    assert int(row['signed_zero_mismatch'])==0,row
    assert int(row['arm_c_bit_difference'])==3,row
    print(implementation,'passes sampled ULP, classification, signed-zero, and ARM comparison gates')
