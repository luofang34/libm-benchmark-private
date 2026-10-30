import fs from 'node:fs';
const [path, scale] = process.argv.slice(2);
const module = await WebAssembly.compile(fs.readFileSync(path));
const imports = WebAssembly.Module.imports(module);
if (imports.length) throw Error(`Unexpected WASM imports: ${JSON.stringify(imports)}`);
const instance = await WebAssembly.instantiate(module);
const tests = [];
if (instance.exports.exponential) {
  for (const x of [-10, -1, 0, 1, 10]) {
    const actual = instance.exports.exponential(x), reference = Math.exp(x);
    if (Math.abs(actual - reference) > Math.abs(reference) * 1e-14) throw Error(`exp(${x}): ${actual}`);
    tests.push({export: 'exponential', input: x, output: actual});
  }
}
if (instance.exports.binary_exponential) {
  for (const x of [-1074, -1022, -10, -1, 0, 1, 10, 1023]) {
    const actual = instance.exports.binary_exponential(x), reference = 2 ** x;
    if (actual !== reference) throw Error(`exp2(${x}): ${actual}`);
    tests.push({export: 'binary_exponential', input: x, output: actual});
  }
}
if (instance.exports.power && instance.exports.power(2, 3) !== 8) throw Error('pow export failed');
if (instance.exports.math_kernel && !Number.isFinite(instance.exports.math_kernel(.5, 2))) throw Error('math kernel failed');
if (scale === 'application') {
  const first = instance.exports.portfolio_report(.04, 30);
  const second = instance.exports.portfolio_report(.05, 30);
  if (first === 0n || first === second) throw Error('portfolio did not consume its inputs');
  tests.push({export: 'portfolio_report', first: first.toString(16), second: second.toString(16)});
}
console.log(JSON.stringify({scale, imports, tests}, null, 2));
