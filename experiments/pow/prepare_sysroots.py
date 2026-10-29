"""Copy installed rust-src; replace only pow and its orphaned word setter."""
from pathlib import Path
import subprocess,shutil
root=Path(__file__).resolve().parent
repo=root.parent.parent
installed=Path(subprocess.check_output(['rustc','+nightly','--print','sysroot'],text=True).strip())/'lib/rustlib/src/rust/library'
for variant in ['base','patched']:
    dst=root/f'sysroot-{variant}/library'
    shutil.copytree(installed,dst,dirs_exist_ok=True)
    if variant=='patched':
        math=dst/'compiler-builtins/libm/src/math'
        shutil.copy2(repo/'libm/src/math/pow.rs',math/'pow.rs')
        shutil.copytree(repo/'libm/src/math/pow',math/'pow',dirs_exist_ok=True)
        p=math/'mod.rs';s=p.read_text();a=s.index('#[inline]\nfn with_set_high_word');b=s.index('#[inline]',a+10);p.write_text(s[:a]+s[b:])
    print(variant,dst)
