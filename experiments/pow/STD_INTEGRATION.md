# pow in Rust std on wasm32-unknown-unknown

## Observed call path

[std f64 source at the measured nightly](https://github.com/rust-lang/rust/blob/41089d07a0a2afc16adfe28a760d94d73d7298a4/library/std/src/num/f64.rs) implements `f64::powf` with `intrinsics::powf`. The [emitted LLVM IR](results/raw/pow-probe.ll) calls `llvm.pow.f64`. The benchmark WAT's `standard` wrapper calls `$pow`; compiler-builtins `src/math/mod.rs::partial_availability` defines `fn pow(x: f64, y: f64) -> f64` and delegates to its included `libm_math::pow`. It includes `../../../libm/src/math/mod.rs` directly. Unix/native uses the platform pow and does not get this replacement through that availability group.

The adjacent `fn powf(x: f32,y: f32)->f32` and `libm/src/math/powf.rs` are the separate single-precision implementation. This patch leaves them unchanged. Nothing here establishes a performance ranking of exp/log/trigonometric functions or investigates sin_cos reduction reuse.

## A versus B

A: the `arm_patch` benchmark calls the modified path dependency's `libm::pow` directly. It proves the algorithm's speed, without changing std.

B: two copies of the installed nightly `rust-src/library` are rebuilt with `-Z build-std=std,panic_abort`. The patched copy replaces only the pow implementation/submodules and removes its unused word-setting helper. The test application still calls ordinary `x.powf(y)`. The minimal size fixture has **no libm or petir dependency**, which independently demonstrates that the std result is not direct dispatch to an application library.

Both copies use Rust commit `41089d07a0a2afc16adfe28a760d94d73d7298a4`, compiler_builtins 0.1.160, the same Cargo lockfiles, and identical release settings. Nightly source is a vendored tree (`17a9e503efa529a41236ef11ef58108f840ccc72`), not assumed to equal the separately cloned repository merely because version numbers match. The Cargo `-vv` logs name the source paths and compiler-builtins artifacts: [baseline](results/raw/build-std-base.log), [patched](results/raw/build-std-patched.log).

Normal positive-input **ordinary std** results, median [p10,p90] ns/op:

| Sysroot | Throughput | Dependency kernel |
|---|---:|---:|
| Rebuilt baseline | 38.009 [37.569, 38.625] | 94.736 [93.476, 105.739] |
| Rebuilt candidate | 11.992 [11.694, 12.143] | 36.666 [36.189, 37.384] |

Throughput speedup: **3.17x**. Dependency-kernel speedup: **2.58x**. Checksums and MPFR results match the candidate's direct path.

## Rebuild command and isolation

```sh
python3 experiments/pow/prepare_sysroots.py
__CARGO_TESTS_ONLY_SRC_ROOT="$PWD/experiments/pow/sysroot-patched/library" \
CARGO_TARGET_DIR="$PWD/experiments/pow/target/sysroot-patched" \
cargo +nightly build --manifest-path experiments/pow/Cargo.toml \
  --lib --release --target wasm32-unknown-unknown \
  -Z build-std=std,panic_abort --locked -vv
```

Replace `patched` with `base` for the control. `__CARGO_TESTS_ONLY_SRC_ROOT` is an internal Cargo testing hook, not a promised stable interface. It works on the recorded Cargo nightly. The source path appears in the actual compile command; an application-level `[patch.crates-io]` is not used to pretend the precompiled sysroot changed. Installed toolchains are untouched. For new users of ordinary precompiled Rust std, this local repository change alone has **no effect**; they must rebuild the sysroot or use a toolchain that includes the change.

The source copy must retain its own module list. Copying a newer checkout's entire math/mod.rs initially failed on a missing unrelated exp2m1f16 module. The reproducible preparation script only deletes the helper and copies pow-specific source. No unresolved Cargo restriction remains for this experiment.

## Real marginal size

All fixtures call ordinary std and differ only by the paired rebuilt sysroot. Release opt-level 3, fat LTO, one codegen unit, abort, symbols stripped. Compression is `gzip -9 -n` and `brotli -q 11`; [size.csv](size.csv) also records raw/gzip/Brotli for `wasm-opt --all-features -O3` and `-Oz` (54 combinations total).

| Fixture | Raw bytes, before → after (delta) | gzip bytes | Brotli bytes |
|---|---:|---:|---:|
| minimal | 2524 → 6674 (+4150) | 1444 → 4894 (+3450) | 1387 → 4660 (+3273) |
| medium | 16565 → 20713 (+4148) | 8199 → 11692 (+3493) | 7489 → 10784 (+3295) |
| application | 128761 → 132973 (+4212) | 57393 → 60944 (+3551) | 49337 → 52544 (+3207) |

Minimal exports only the pow interface. Medium also links exp, exp2, ln, log2, sin_cos and atan2. The 129 KB representative application performs JSON parsing, cash-flow discounting/duration calculations, and JSON serialization, with runtime-supplied rates/periods and a consumed output hash. It is a computational fixture, not random padding or a production application. Executable checks exercise all six baseline/candidate modules and verify no host math imports. Results cannot be extrapolated to every large WASM product; no production application was measured.

The candidate contains a 3,072-byte logarithm table and a 2,048-byte exponential table. Each entire table occurs exactly once in each candidate binary ([evidence](results/raw/table-sharing.json)). Other existing libm exp/log algorithms use different tables or polynomial data, so adding them does not produce genuine table sharing. The measured gzip marginal cost is slightly larger in the application than in the minimal module, while Brotli's is smaller; a bigger app does not guarantee a smaller compressed delta.

## Decision

This is a viable candidate for a narrowly scoped f64 pow proposal: the A and B speedups are measured, permissive provenance is retained, and finite MPFR accuracy improves in the tested sample. It is not ready to submit unchanged: approximately 3.1–3.6 KB extra compressed application code, table maintenance, small/special-domain performance, rounding-mode/fenv expectations, and additional target/MSRV testing need maintainer agreement. The portable non-FMA path avoids target-specific intrinsics and builds on a non-WASM no_std fallback. Native Apple system pow remains faster; no native std speedup is claimed. Other functions have not been ranked because the requested patch scope is pow.
