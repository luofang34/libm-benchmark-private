"""Execute P0, P2, P3 and P4 locally; no remote writes or installed sysroot edits."""
from pathlib import Path
import subprocess,os,json,hashlib
root=Path(__file__).resolve().parent
repo=root.parent.parent
raw=root/'results/raw';art=root/'results/artifacts'
raw.mkdir(parents=True,exist_ok=True);art.mkdir(parents=True,exist_ok=True)

def run(args,name,env=None):
    with (raw/(name+'.log')).open('w') as log:
        subprocess.run([str(x) for x in args],cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)

def csv_run(args,name):
    with (raw/(name+'.csv')).open('w') as out:
        subprocess.run([str(x) for x in args],cwd=repo,stdout=out,check=True)

run(['python3',root/'prepare_sources.py'],'prepare-sources')
run(['cargo','fetch','--manifest-path',root/'Cargo.toml','--locked'],'fetch-harness')
run(['cargo','fetch','--manifest-path',root/'fixtures/Cargo.toml','--locked'],'fetch-fixtures')
run(['python3',root/'prepare_sysroots.py'],'prepare-sysroots')
base=['cargo','build','--manifest-path',root/'Cargo.toml','--release','--locked']
run(base,'build-native')
run(base+['--lib','--target','wasm32-unknown-unknown'],'build-wasm')
for variant in ['base','patched']:
    env=os.environ.copy();env['__CARGO_TESTS_ONLY_SRC_ROOT']=str(root/f'sysroot-{variant}/library');env['CARGO_TARGET_DIR']=str(root/f'target/sysroot-{variant}')
    run(['cargo','+nightly','build','--manifest-path',root/'Cargo.toml','--lib','--release','--target','wasm32-unknown-unknown','-Zbuild-std=std,panic_abort','--locked','-vv'],'build-std-'+variant,env)
run(['clang++','-O3','-std=c++17','-fno-builtin-pow','-ffp-contract=off',root/'cpp_bench.cpp','-o',art/'cpp_bench'],'build-cpp')
# Timed jobs run sequentially after every build job has completed.
csv_run([art/'cpp_bench'],'cpp')
csv_run([root/'target/release/pow-experiment'],'native')
for variant,path,label in [('wasm','target','wasm'),('wasm-rebuilt-base','target/sysroot-base','wasm_rebuilt_base'),('wasm-rebuilt-patch','target/sysroot-patched','wasm_rebuilt_patch')]:
    csv_run(['node',root/'bench.mjs',root/path/'wasm32-unknown-unknown/release/pow_experiment.wasm',label],variant)
run(['python3',root/'summarize.py'],'summarize')
run(['python3',root/'size.py'],'size-run')
run(['node',root/'verify.mjs'],'fixture-verification')
run(['python3',root/'accuracy_inputs.py'],'accuracy-inputs')
run(['node',root/'accuracy.mjs'],'accuracy-wasm')
arm=root/'vendor/optimized-routines/math'
cmd=['clang','-O3','-fno-builtin-pow','-ffp-contract=off','-DHAVE_FAST_FMA=0','-DHAVE_FAST_ROUND=0','-DUSE_GLIBC_ABI=0','-DWANT_ROUNDING=0','-Dpow=arm_pow','-I',arm,'-I',arm/'include','-I','/opt/homebrew/include',root/'mpfr_check.c']
cmd += [arm/x for x in ['pow.c','pow_log_data.c','exp_data.c','math_err.c']]
cmd += ['-L','/opt/homebrew/lib','-lmpfr','-lgmp','-o',art/'mpfr_check']
run(cmd,'build-mpfr')
with (raw/'accuracy.csv').open('w') as out,(raw/'mpfr.log').open('w') as log:
    subprocess.run([art/'mpfr_check',art/'outputs.bin',raw/'accuracy-domains.txt'],stdout=out,stderr=log,check=True)
run(['python3',root/'verify_accuracy.py'],'accuracy-gates')
run(['python3',root/'check_tables.py'],'tables-check')
print('Completed measurements; CSV files and raw logs are in',root)
