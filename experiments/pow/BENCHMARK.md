# Pow hardware-test experiment

Scope: double-precision `libm::pow` and ordinary Rust `f64::powf` only, hosted in a private repository for hardware testing. `powf(f32)` and the P1 function ranking are outside this patch. Measurements were collected on 2026-10-29.

## Source and environment

| Component | Identity |
|---|---|
| compiler-builtins checkout | `6bc104a50f83cb205790c61c5d33508046f5fad3` |
| checkout libm / compiler_builtins | 0.2.16 / 0.1.160 |
| registry libm 0.2.16 | `dfd2203a4d6110820ad7bb65cafe1bf331a03a3d`; checksum in Cargo.lock |
| petir 0.0.3 | `f2205d867dfe44c3fc7478656f6f5ae56390f984`; default features disabled |
| ARM reference | `2ee4b0d45680a9880412c1d186224b08652c35f6` |
| Rust stable | 1.99.0, `b940084d7eb6a299eb4bfeb8e34901bc051e7ac4`, LLVM 23.1.1 |
| Rust nightly for paired sysroots | 1.101.0-nightly, `41089d07a0a2afc16adfe28a760d94d73d7298a4`, LLVM 23.1.4 |
| nightly compiler-builtins source tree | `17a9e503efa529a41236ef11ef58108f840ccc72`, package 0.1.160 |
| stable compiler-builtins source package | 0.1.160 |
| Cargo | stable 1.99.0 (`5f94df478`), nightly 1.101.0-nightly (`cad07cf8e`) |
| Clang | Apple 21.0.0 (`clang-2100.4.1.1`) |
| Node / V8 | 26.12.1 / 14.6.202.34-node.40 |
| Machine | Apple M3 Max, macOS 27.0, build 26A5368g, aarch64 |
| Tools | Binaryen 128; Brotli 1.2.1; MPFR 4.2.2 |

Full version output and source hashes: [environment.json](results/environment.json). The registry and checkout `pow` implementation bodies are identical; only two test cfg annotations differ ([diff](results/raw/libm-baseline-source.diff)). The initial user harness is preserved in `original/`; its PRNG was in the timed loop. Its tiny C++ result is not used as a baseline.

The candidate was transcribed from [ARM's permissive C implementation](https://github.com/ARM-software/optimized-routines/blob/2ee4b0d45680a9880412c1d186224b08652c35f6/math/pow.c), using the non-FMA branch. Tables are extracted from compiled ARM objects; [check_tables.py](check_tables.py) compares every coefficient and all 640 table words. The unused padding in the C logarithm table is omitted. Petir is a comparison dependency only; its GPL/AGPL Rust source is not incorporated into the candidate. Its module cites ARM commit `f2e4faf58c6c671154f472a76eaaa977bb36c870`.

## Method and validity

- Release, opt-level 3, fat LTO, one codegen unit, abort on panic; no fast-math or software FMA. Same wrappers and loops for all four implementations. Dispatch occurs outside the timed kernel.
- Each trial prepares 16,384 input pairs before timing, then executes 32 passes (524,288 calls). The PRNG seed is 2026. Every output contributes to a wrapping integer checksum; input `black_box` barriers and non-inlined wrappers prevent constant folding or loop-invariant hoisting.
- Throughput has four independent checksum accumulators and independent input pairs. Dependency latency feeds the preceding result's low 8 bits into the next base's mantissa; it includes bit feedback and checksum overhead. This preserves the general input domain but is a dependent **kernel** latency, not an isolated hardware instruction latency. For special values, feedback chooses the next array index so the IEEE values remain intact; that feedback can change the mixture and should not be used as a pure function latency comparison.
- WASM executes the entire loop internally. The host clock is called only at the start/end of a trial and reporting occurs after timing, never once per pow. JS does not execute the mathematical loop.
- Five warmup rounds per domain/mode, followed by 15 measured rounds. Implementations rotate order each round. Timed processes run sequentially without concurrent compilation. These are interactive macOS measurements, not isolated-core or fixed-frequency measurements.
- Median and linearly interpolated p10/p90 are reported without trimming or subtracting overhead. `control` measures the same loop around an add. For normal inputs its WASM throughput is 0.529 ns/op and dependency time 4.728 ns/op.
- Input domains: positive x in [0.5,2), y in [-8,8); x within 1e-8 of 1 with |y| up to 1e10; negative x with integer y in [-16,16]; positive subnormal bases with y in [0.2,1.5); bases near 2 with exponents near 1024/-1075; a separate 16-pair zero/infinity/NaN/domain-error set. See [inputs.rs](src/inputs.rs) for exact formulas.

## P0 results

This table records the initial algorithm comparison. The compile-time scoped source `f39774d821b2bbc19c98dca827678fdce636d075` has a separate [WASM rerun](../../benchmarks/results/raw-logs/target-scope/std/performance.csv) and [default/native CPU hardware evidence](../../benchmarks/reports/architecture-comparison.md#hosted-hardware-comparison). These populations are retained separately.

Normal positive inputs, ns/call: median [p10, p90].

| Runtime | Implementation | Independent throughput | Dependency kernel |
|---|---|---:|---:|
| native | libm_old | 46.300 [35.833, 63.381] | 91.634 [90.786, 99.866] |
| native | petir | 9.970 [9.400, 13.704] | 37.164 [36.711, 42.982] |
| native | std | 8.352 [7.639, 15.320] | 33.303 [32.507, 34.672] |
| native | arm_patch | 11.260 [9.724, 20.482] | 37.229 [36.880, 40.774] |
| wasm | libm_old | 36.824 [36.154, 37.653] | 109.362 [98.141, 153.726] |
| wasm | petir | 13.130 [12.824, 13.516] | 46.673 [41.421, 61.638] |
| wasm | std | 38.005 [37.069, 38.558] | 115.072 [99.516, 142.407] |
| wasm | arm_patch | 12.061 [11.671, 12.382] | 44.598 [38.200, 59.795] |

The direct candidate is **3.05x** faster than old libm in normal WASM throughput; petir is **2.80x** faster. This does not imply 3x across all input distributions:

| Domain | Old libm throughput | Candidate throughput |
|---|---:|---:|
| positive | 36.824 [36.154, 37.653] | 12.061 [11.671, 12.382] |
| near_one | 31.667 [23.454, 67.399] | 19.926 [12.565, 32.921] |
| negative_integer | 34.273 [32.976, 88.216] | 13.320 [12.956, 51.595] |
| subnormal | 37.534 [35.887, 38.639] | 22.185 [20.856, 24.590] |
| range_edge | 34.168 [33.229, 34.932] | 22.335 [21.928, 23.342] |
| special | 4.464 [4.280, 4.771] | 4.429 [4.343, 4.631] |

Every domain/mode/runtime combination, including controls, is in [performance.csv](performance.csv); all 3,600 measured trial rows and checksums are in [results/raw](results/raw). Normal throughput checksums are `b32f2dd38b6cb340` (old libm and unpatched WASM std), `b32f2dd38b6cb820` (petir/candidate/patched std), and `b32f2dd38b6cb700` (native platform std/C++). Different last-bit results are expected; the MPFR comparison evaluates them independently. Dependency checksums may differ because results influence subsequent bases. NaN payload equality is not a requirement.

Corrected C++ native median: **8.862 ns/op**, 15 rounds, same precomputed positive inputs and bit checksum. `-fno-builtin-pow`, a non-inlined wrapper, and per-input compiler barriers keep calls alive. [Assembly](results/raw/cpp_bench.s) contains `bl __Z12measured_powdd` in the inner loop and that wrapper branches to `_pow`. C++ uses `double std::pow(double,double)`; Rust f64 lowers to `llvm.pow.f64` and the C ABI `double pow`, not `float powf`.

## Patch and retained artifacts

The standalone [libm-pow-arm.patch](libm-pow-arm.patch) applies to checkout `6bc104a50f83cb205790c61c5d33508046f5fad3` and is already applied on the `experiment/pow-wasm` branch. It changes only f64 pow, its lookup data/tests, target selection and preserved fdlibm fallback. The selector enables WASM unknown, AArch64 macOS/GNU Linux with NEON, and x86-64 GNU Linux/Windows MSVC with SSE2. The fallback arithmetic is preserved with its helper localized. The experimental harness, private workflow and logs are outside the seven-file patch. Forward/reverse application and byte equality against the tested source are [verified](../../benchmarks/results/raw-logs/target-scope/patch-verification.json).

The actual tested WASM modules are retained in `results/wasm/`, with SHA-256 values in `results/artifact-manifest.json`. `inputs.bin.gz`, `outputs.bin.gz`, and `accuracy-domains.txt.gz` preserve the raw accuracy stream and labels. Each output record contains eight little-endian u64 bit patterns: x, y, old libm, petir, stable std, candidate, rebuilt baseline std, rebuilt candidate std. To check the archived fixtures without rebuilding:

```sh
node experiments/pow/verify.mjs ./results/wasm/
python3 experiments/pow/verify_accuracy.py
```

Compilation caches and copied sysroots were cleaned after validation. The user-provided temporary powbench directory was cleaned and removed after preserving its source under `original/`. The full reproduction script regenerates disposable inputs and builds.

## Reproduce

From the repository root, with the recorded stable/nightly toolchains, nightly rust-src, wasm32-unknown-unknown targets, Node, Clang, Binaryen, Brotli and Homebrew MPFR/GMP installed:

```sh
python3 experiments/pow/run.py
python3 experiments/pow/check_tables.py
```

`prepare_sources.py` checks compiler SHAs and the ARM source-file hashes. The Cargo lockfiles pin package sources. A different nightly alias is rejected rather than silently treated as the recorded experiment. `run.py` contains the actual native/WASM/C++/MPFR commands; it writes raw logs and CSVs. Table and source generation use no external AI services. Downloaded sources and compiler caches are disposable; retained evidence is independent of those caches.

For P0 alone:

```sh
cargo build --manifest-path experiments/pow/Cargo.toml --release --locked
cargo build --manifest-path experiments/pow/Cargo.toml --release --lib --target wasm32-unknown-unknown --locked
experiments/pow/target/release/pow-experiment
node experiments/pow/bench.mjs experiments/pow/target/wasm32-unknown-unknown/release/pow_experiment.wasm
```

## Validation and limits

- Debug and Release libm unit tests: **114 passed** in each, including signed-zero, signaling-NaN identities, minimum subnormal, and a difficult logarithm-reduction regression.
- Clippy with `-D warnings`: libm, benchmark harness, and all fixture features pass. Formatting passes. Generated tables agree with the compiled ARM reference.
- The candidate remains `no_std`. Eleven actual target builds enforce selection/table omission; Rust 1.67.0 builds the library-only production source for AArch64 macOS, WASM and Cortex-M fallback. Eight default/native hosted configurations each pass 151,083 MPFR cases. Ten pow tests pass with no-panic verification; the upstream MPFR extensive harness passes 1,000,000 spaced pairs. Logs are in [target-scope/gates](../../benchmarks/results/raw-logs/target-scope/gates/).
- Strict `RUSTDOCFLAGS="-D missing_docs -D broken_intra_doc_links" cargo doc -p libm --no-deps` fails on existing public functions outside pow. The identical gate also fails on an unmodified baseline copy: [baseline](results/raw/doc-baseline.log), [candidate](results/raw/doc-libm.log). No unrelated documentation or lint policy is changed. No claim is made that all repository CI jobs passed.
- The repository has no `scripts/check-structure.sh` or `quality-gates` job. The standalone math patch does not alter upstream CI. Manual evidence workflows exist only in the private benchmark repository.
- See [STD_INTEGRATION.md](STD_INTEGRATION.md), [size.csv](size.csv), and [accuracy.md](accuracy.md) for integration, marginal size, and accuracy evidence. The patch is intended for private hardware testing.
