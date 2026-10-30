import fs from 'node:fs';
const [basePath, candidatePath, repeatsText = '32', scope = 'direct'] = process.argv.slice(2);
const repeats = Number(repeatsText);
let result;
const imports = {env: {
  clock_ms: () => performance.now(),
  report: (ns, checksum, calls) => { result = {ns, checksum, calls: Number(calls)}; },
}};
const load = async path => (await WebAssembly.instantiate(fs.readFileSync(path), imports)).instance;
const instances = [await load(basePath), await load(candidatePath)];
const choices = scope === 'sysroot'
  ? [[0, 1, 'std_rebuilt_base'], [1, 1, 'std_rebuilt_candidate'], [0, 2, 'control']]
  : [[0, 0, 'libm_base'], [1, 0, 'libm_candidate'], [0, 1, 'std_prebuilt_sysroot'], [0, 2, 'control']];
const domains = ['normal', 'near_zero', 'subnormal_input', 'subnormal_output', 'range_edge', 'special'];
console.log('runtime,function,implementation,domain,mode,round,ns_per_op,checksum,calls');
for (const [functionIndex, name] of ['exp', 'exp2'].entries()) {
  for (const [domain, distribution] of domains.entries()) {
    for (const [mode, modeName] of ['throughput', 'dependency_kernel'].entries()) {
      for (let iteration = 0; iteration < 20; iteration++) {
        for (let offset = 0; offset < choices.length; offset++) {
          const [variant, kind, implementation] = choices[(offset + iteration) % choices.length];
          instances[variant].exports.run_bench(functionIndex, kind, mode, domain, repeats);
          if (result.calls !== 16384 * repeats) throw Error('incomplete WASM timing loop');
          if (iteration >= 5) {
            console.log([scope === 'sysroot' ? 'wasm_sysroot_node' : 'wasm_node', name, implementation, distribution, modeName, iteration - 5,
              result.ns / result.calls, BigInt.asUintN(64, result.checksum).toString(16).padStart(16, '0'),
              result.calls].join(','));
          }
        }
      }
    }
  }
}
