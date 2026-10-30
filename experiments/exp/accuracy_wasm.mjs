import fs from 'node:fs';
const [inputsPath, basePath, candidatePath, outputPath] = process.argv.slice(2);
const imports = {env: {clock_ms: () => 0, report: () => {}}};
const load = async path => (await WebAssembly.instantiate(fs.readFileSync(path), imports)).instance;
const base = await load(basePath), candidate = await load(candidatePath);
const inputs = fs.readFileSync(inputsPath), output = Buffer.alloc(inputs.length / 16 * 40);
for (let index = 0; index < inputs.length / 16; index++) {
  const functionIndex = inputs.readBigUInt64LE(index * 16);
  const word = inputs.readBigUInt64LE(index * 16 + 8);
  const results = [functionIndex, word,
    base.exports.unary_bits(Number(functionIndex), 0, word),
    candidate.exports.unary_bits(Number(functionIndex), 0, word),
    base.exports.unary_bits(Number(functionIndex), 1, word)];
  results.forEach((result, field) => output.writeBigUInt64LE(BigInt.asUintN(64, result), index * 40 + field * 8));
}
fs.writeFileSync(outputPath, output);
console.log(`Evaluated ${inputs.length / 16} actual WASM cases; std uses the prebuilt sysroot.`);
