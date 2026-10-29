"""Compare every generated coefficient and table entry with compiled ARM data."""
from pathlib import Path
import subprocess,re,ast
root=Path(__file__).resolve().parent
arm=root/'vendor/optimized-routines/math'
exe=root/'results/artifacts/dump_tables'
subprocess.run(['clang','-O2','-DHAVE_FAST_FMA=0','-DHAVE_FAST_ROUND=0','-DUSE_GLIBC_ABI=0','-I',str(arm),str(root/'dump_tables.c'),str(arm/'pow_log_data.c'),str(arm/'exp_data.c'),'-o',str(exe)],check=True)
generated=subprocess.check_output([exe],text=True)
actual=(root.parent.parent/'libm/src/math/pow/table.rs').read_text()
def constants(text):
    return {name:ast.literal_eval(value) for name,value in re.findall(r'pub\(super\) const (\w+):.*? = (.*?);',text,re.S)}
assert constants(actual)==constants(generated)
print('All coefficients and 640 table words match compiled ARM data.')
