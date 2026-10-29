import fs from 'node:fs';
const [path, label = 'wasm'] = process.argv.slice(2);
let result;
const {instance} = await WebAssembly.instantiate(fs.readFileSync(path), {env: {
  clock_ms: () => performance.now(),
  report: (ns, checksum, calls) => { result = {ns,checksum: BigInt.asUintN(64,checksum).toString(16).padStart(16,'0'),calls}; }
}});
const names = ['libm_old','petir','std','arm_patch','control'];
const domains = ['positive','near_one','negative_integer','subnormal','range_edge','special'];
console.log('runtime,implementation,domain,mode,round,ns_per_op,checksum,calls');
for(let domain=0;domain<6;domain++) for(let mode=0;mode<2;mode++) {
  for(let round=0;round<20;round++) for(let offset=0;offset<5;offset++) {
    const kind=(offset+round)%5;
    instance.exports.run_bench(kind,mode,domain,32);
    if(round>=5) console.log([label,names[kind],domains[domain],mode?'dependency':'throughput',round-5,(result.ns/result.calls).toFixed(6),result.checksum,result.calls].join(','));
  }
}
