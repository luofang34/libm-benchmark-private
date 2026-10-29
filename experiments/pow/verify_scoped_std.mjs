import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const [modulePath, outputDirectory] = process.argv.slice(2);
assert(modulePath && outputDirectory, 'usage: node verify_scoped_std.mjs MODULE OUTPUT_DIRECTORY');
const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const root = new URL('./results/raw/', import.meta.url);
const inputs = zlib.gunzipSync(fs.readFileSync(new URL('inputs.bin.gz', root)));
const domains = zlib.gunzipSync(fs.readFileSync(new URL('accuracy-domains.txt.gz', root)))
  .toString().trim().split('\n');
const archived = zlib.gunzipSync(fs.readFileSync(new URL('outputs.bin.gz', root)));
const bytes = fs.readFileSync(modulePath);
const {instance} = await WebAssembly.instantiate(bytes, {env: {
  clock_ms: () => performance.now(), report: () => {},
}});
const isNaN = bits => (bits & 0x7fffffffffffffffn) > 0x7ff0000000000000n;
const equivalent = (a, b) => a === b || (isNaN(a) && isNaN(b));
assert.equal(inputs.length, 151083 * 16);
assert.equal(archived.length, 151083 * 64);
assert.equal(domains.length, 151083);
const lines = ['test_distribution,index,x_bits,y_bits,baseline_bits,candidate_bits'];
const hex = bits => bits.toString(16).padStart(16, '0');
for (let i = 0; i < domains.length; i++) {
  const x = inputs.readBigUInt64LE(i * 16);
  const y = inputs.readBigUInt64LE(i * 16 + 8);
  assert.equal(archived.readBigUInt64LE(i * 64), x);
  assert.equal(archived.readBigUInt64LE(i * 64 + 8), y);
  const baseline = archived.readBigUInt64LE(i * 64 + 16);
  const expected = archived.readBigUInt64LE(i * 64 + 56);
  const standard = BigInt.asUintN(64, instance.exports.pow_bits(2, x, y));
  const direct = BigInt.asUintN(64, instance.exports.pow_bits(3, x, y));
  assert(equivalent(standard, expected), `std differs from archived candidate at ${i}`);
  assert(equivalent(standard, direct), `std differs from direct libm at ${i}`);
  lines.push([domains[i], i, hex(x), hex(y), hex(baseline), hex(standard)].join(','));
}
fs.mkdirSync(outputDirectory, {recursive: true});
const csv = lines.join('\n') + '\n';
fs.writeFileSync(path.join(outputDirectory, 'accuracy-bits.csv'), csv);
fs.writeFileSync(path.join(outputDirectory, 'manifest.json'), JSON.stringify({
  cases: domains.length, module_sha256: sha256(bytes), input_sha256: sha256(inputs),
  output_sha256: sha256(csv), node: process.version, v8: process.versions.v8,
  checks: ['ordinary std equals direct libm', 'ordinary std equals archived candidate'],
  comparison: 'exact bits for non-NaN results; NaN classification without payload equality',
  reference: 'MPFR validation is separate; these equality checks are not an accuracy proof',
}, null, 2) + '\n');
console.log(`${domains.length} ordinary std outputs match direct libm and archived candidate`);
