"""Build identical fixtures against baseline/patched sysroots and measure actual deltas."""
from pathlib import Path
import subprocess,os,csv
root=Path(__file__).resolve().parent
raw=root/'results/raw';art=root/'results/artifacts'
rows=[]
for variant in ['base','patched']:
    env=os.environ.copy()
    env['__CARGO_TESTS_ONLY_SRC_ROOT']=str(root/f'sysroot-{variant}/library')
    env['CARGO_TARGET_DIR']=str(root/f'target/size-{variant}')
    for fixture,features in [('minimal',[]),('medium',['medium']),('application',['application'])]:
        cmd=['cargo','+nightly','build','--manifest-path',str(root/'fixtures/Cargo.toml'),'--release','--lib','--target','wasm32-unknown-unknown','-Zbuild-std=std,panic_abort','--offline']
        if features:cmd+=['--features',','.join(features)]
        with (raw/f'build-size-{variant}-{fixture}.log').open('w') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        source=root/f'target/size-{variant}/wasm32-unknown-unknown/release/pow_fixture.wasm'
        original=art/f'{fixture}-{variant}.wasm';original.write_bytes(source.read_bytes())
        for optimization in ['none','O3','Oz']:
            output=original if optimization=='none' else art/f'{fixture}-{variant}-{optimization}.wasm'
            if optimization!='none':subprocess.run(['wasm-opt','--all-features',f'-{optimization}',str(original),'-o',str(output)],check=True)
            data=output.read_bytes()
            gzip=subprocess.check_output(['gzip','-9','-n','-c'],input=data)
            brotli=subprocess.check_output(['brotli','-q','11','-c'],input=data)
            for encoding,size in [('raw',len(data)),('gzip',len(gzip)),('brotli',len(brotli))]:
                rows.append(dict(fixture=fixture,variant=variant,optimization=optimization,encoding=encoding,bytes=size))
for row in rows:
    base=next(r['bytes'] for r in rows if r['fixture']==row['fixture'] and r['optimization']==row['optimization'] and r['encoding']==row['encoding'] and r['variant']=='base')
    row['delta_from_baseline']=row['bytes']-base
with (root/'size.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('Measured',len(rows),'fixture/encoding/optimization combinations.')
