import fs from 'node:fs';
const [modulePath, tablePath, mode = 'standalone'] = process.argv.slice(2);
const module = await WebAssembly.compile(fs.readFileSync(modulePath));
const imports = WebAssembly.Module.imports(module);
const allowed = mode === 'timed' && imports.every(item => item.module === 'env' &&
  item.kind === 'function' && ['clock_ms', 'report'].includes(item.name));
if (imports.length && !allowed) throw Error(`Unexpected WASM imports: ${JSON.stringify(imports)}`);
const instance = await WebAssembly.instantiate(module, {env: {clock_ms: () => 0, report: () => {}}});
const memory = Buffer.from(instance.exports.memory.buffer);
const table = fs.readFileSync(tablePath);
const offsets = [];
for (let offset = memory.indexOf(table); offset >= 0; offset = memory.indexOf(table, offset + 1)) {
  offsets.push(offset);
}
console.log(JSON.stringify({imports, table_occurrences: offsets.length, table_offsets: offsets,
  initial_memory_bytes: memory.length, table_bytes: table.length}));
