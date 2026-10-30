import json,os,pathlib,subprocess,sys,time
root=pathlib.Path('/Users/fangluo/Documents/ChatGPT/libm')
out=root/'benchmarks/results/raw-logs/contribution-validation'
name=sys.argv[1]; cmd=sys.argv[2:]
env=os.environ | {'RUSTUP_TOOLCHAIN':'nightly','CARGO_TERM_COLOR':'never','LIBM_SEED':'0123456789abcdef0123456789abcdef'}
start=time.time()
with (out/(name+'.log')).open('w') as stream:
 stream.write('$ '+repr(cmd)+'\n');stream.flush()
 r=subprocess.run(cmd,cwd=env.get('VALIDATION_CWD',root),env=env,stdout=stream,stderr=subprocess.STDOUT)
record={'command':cmd,'environment':{k:v for k,v in env.items() if k.startswith(('RUST','CARGO','LIBM','TO_TEST','VALIDATION','DOCKER')) and 'TOKEN' not in k},'exit_code':r.returncode,'elapsed_seconds':time.time()-start}
(out/(name+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(name,record['exit_code'],record['elapsed_seconds'],flush=True)
sys.exit(r.returncode)
