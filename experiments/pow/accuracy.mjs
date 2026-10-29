import fs from 'node:fs';
const root=new URL('./',import.meta.url);
const load=async path=>(await WebAssembly.instantiate(fs.readFileSync(new URL(path,root)),{env:{clock_ms:()=>0,report:()=>{}}})).instance;
const direct=await load('target/wasm32-unknown-unknown/release/pow_experiment.wasm');
const baseline=await load('target/sysroot-base/wasm32-unknown-unknown/release/pow_experiment.wasm');
const patched=await load('target/sysroot-patched/wasm32-unknown-unknown/release/pow_experiment.wasm');
const input=fs.readFileSync(new URL('results/artifacts/inputs.bin',root));
const output=Buffer.alloc(input.length*4);
for(let i=0;i<input.length/16;i++) {
  const x=input.readBigUInt64LE(i*16), y=input.readBigUInt64LE(i*16+8);
  input.copy(output,i*64,i*16,i*16+16);
  const values=[...[0,1,2,3].map(k=>direct.exports.pow_bits(k,x,y)),baseline.exports.pow_bits(2,x,y),patched.exports.pow_bits(2,x,y)];
  values.forEach((v,j)=>output.writeBigUInt64LE(BigInt.asUintN(64,v),i*64+(j+2)*8));
}
fs.writeFileSync(new URL('results/artifacts/outputs.bin',root),output);
console.log(`Evaluated ${input.length/16} inputs through actual WASM exports.`);
