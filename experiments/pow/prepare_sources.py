"""Fetch the pinned permissive ARM reference and verify benchmark toolchains."""
from pathlib import Path
import subprocess,tarfile,urllib.request,io,hashlib,json
root=Path(__file__).resolve().parent
arm_sha='2ee4b0d45680a9880412c1d186224b08652c35f6'
for tool,sha in [('rustc','b940084d7eb6a299eb4bfeb8e34901bc051e7ac4'),('rustc +nightly','41089d07a0a2afc16adfe28a760d94d73d7298a4')]:
    output=subprocess.check_output(tool.split()+['-vV'],text=True)
    if sha not in output:raise RuntimeError(f'{tool} differs from the recorded toolchain; select the matching toolchain before reproducing')
(root/'vendor').mkdir(exist_ok=True)
arm=root/'vendor/optimized-routines'
if not arm.exists():
    with urllib.request.urlopen(f'https://codeload.github.com/ARM-software/optimized-routines/tar.gz/{arm_sha}') as r:data=r.read()
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:archive.extractall(root/'vendor',filter='data')
    (root/f'vendor/optimized-routines-{arm_sha}').rename(arm)
for name,digest in json.loads((root/'reference-source-sha256.json').read_text()).items():
    assert hashlib.sha256((arm/name).read_bytes()).hexdigest()==digest,name
(root/'results/artifacts').mkdir(parents=True,exist_ok=True)
(root/'results/raw').mkdir(parents=True,exist_ok=True)
print('Pinned ARM reference and toolchains ready.')
