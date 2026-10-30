import fs from 'node:fs';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
const wasm = fs.readFileSync(process.argv[2]);
const module = new WebAssembly.Module(wasm);
assert.deepEqual(WebAssembly.Module.imports(module), []);
assert.deepEqual(WebAssembly.Module.exports(module), [
    {name: 'memory', kind: 'memory'}, {name: 'pow_bits', kind: 'function'}
]);
const instance = new WebAssembly.Instance(module);
const rows = zlib.gunzipSync(fs.readFileSync(process.argv[3])).toString().trim().split('\n').slice(1);
const nan = bits => (bits & 0x7fffffffffffffffn) > 0x7ff0000000000000n;
let nanPairs = 0;
for (const row of rows) {
    const [domain, index, x, y, baseline, candidate] = row.split(',');
    const expected = BigInt('0x' + candidate);
    const actual = BigInt.asUintN(64, instance.exports.pow_bits(BigInt('0x' + x), BigInt('0x' + y)));
    if (nan(actual) && nan(expected)) nanPairs++;
    else assert.equal(actual, expected, `${domain}/${index}`);
}
console.log(JSON.stringify({inputs: rows.length, nanPairs, nonNanBitMismatches: 0,
    imports: WebAssembly.Module.imports(module), exports: WebAssembly.Module.exports(module)}, null, 2));
