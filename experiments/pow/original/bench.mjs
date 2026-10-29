import { readFileSync, statSync } from "node:fs";
import { performance } from "node:perf_hooks";

const path = "target/wasm32-unknown-unknown/release/powbench.wasm";
const bytes = readFileSync(path);
const { instance } = await WebAssembly.instantiate(bytes, {});

console.log("WASM bytes:", statSync(path).size);

for (const name of ["bench_libm", "bench_arm", "bench_std"]) {
    const f = instance.exports[name];
    f(100_000); // warm-up
    const times = [];
    let checksum;

    for (let i = 0; i < 7; i++) {
        const start = performance.now();
        checksum = f(2_000_000);
        times.push((performance.now() - start) * 1e6 / 2_000_000);
    }
    times.sort((a,b) => a-b);
    console.log(name, times[3].toFixed(2),
                "ns/op", "sum=", checksum);
}
