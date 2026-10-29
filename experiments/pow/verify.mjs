import fs from 'node:fs';
import assert from 'node:assert/strict';
const root=new URL(process.argv[2] || './results/artifacts/',import.meta.url);
const suffix=process.argv[3] ? `-${process.argv[3]}` : '';
for(const variant of ['base','patched']) for(const fixture of ['minimal','medium','application']) {
  const module=await WebAssembly.compile(fs.readFileSync(new URL(`${fixture}-${variant}${suffix}.wasm`,root)));
  assert.equal(WebAssembly.Module.imports(module).length,0);
  const instance=await WebAssembly.instantiate(module);
  assert.equal(instance.exports.power(2,10),1024);
  assert.equal(Object.is(instance.exports.power(-2,-1075),-0),true);
  if(fixture!=='minimal')assert(Number.isFinite(instance.exports.math_kernel(1.2,2.3)));
  if(fixture==='application') {
    const a=instance.exports.portfolio_report(.03,30);
    assert.equal(a,instance.exports.portfolio_report(.03,30));
    assert.notEqual(a,instance.exports.portfolio_report(.04,30));
  }
  console.log(`${fixture}/${variant}${suffix}: executes, no host math imports, input changes consumed`);
}
