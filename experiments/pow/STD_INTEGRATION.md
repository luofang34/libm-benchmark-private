# pow in Rust std on wasm32-unknown-unknown

## Observed call path

[std f64 source at the measured nightly](https://github.com/rust-lang/rust/blob/41089d07a0a2afc16adfe28a760d94d73d7298a4/library/std/src/num/f64.rs) implements `f64::powf` with `intrinsics::powf`. The [emitted LLVM IR](results/raw/pow-probe.ll) calls `llvm.pow.f64`. The [scoped benchmark WAT](../../benchmarks/results/raw-logs/target-scope/std/module.wat.gz)'s `standard` wrapper calls `$pow`; compiler-builtins `src/math/mod.rs::partial_availability` defines `fn pow(x: f64, y: f64) -> f64` and delegates to its included `libm_math::pow`. It includes `../../../libm/src/math/mod.rs` directly. Unix/native uses the platform pow and does not get this replacement through that availability group.

The adjacent `fn powf(x: f32,y: f32)->f32` and `libm/src/math/powf.rs` are the separate single-precision implementation. This patch leaves them unchanged. Nothing here establishes a performance ranking of exp/log/trigonometric functions or investigates sin_cos reduction reuse.

## A versus B

A: the `arm_patch` benchmark calls the modified path dependency's `libm::pow` directly. It proves the algorithm's speed, without changing std.

B: two copies of the installed nightly `rust-src/library` are rebuilt with `-Z build-std=std,panic_abort`. The patched copy installs the pow implementation/submodules, explicit target selector and fdlibm fallback, and localizes the fallback word-setting helper. The test application still calls ordinary `x.powf(y)`. The minimal size fixture has **no libm or petir dependency**, which independently demonstrates that the std result is not direct dispatch to an application library.

Both copies use Rust commit `41089d07a0a2afc16adfe28a760d94d73d7298a4`, compiler_builtins 0.1.160, the same Cargo lockfiles, and identical release settings. Nightly source is a vendored tree (`17a9e503efa529a41236ef11ef58108f840ccc72`), not assumed to equal the separately cloned repository merely because version numbers match. The Cargo `-vv` logs name the source paths and compiler-builtins artifacts: [baseline](results/raw/build-std-base.log), [scoped candidate](../../benchmarks/results/raw-logs/target-scope/gates/build-std-scoped.log). Candidate math source is `f39774d821b2bbc19c98dca827678fdce636d075`; its standalone patch is verified against checkout `6bc104a50f83cb205790c61c5d33508046f5fad3`.

Normal positive-input **ordinary std** results, median [p10,p90] ns/op:

| Sysroot | Throughput | Dependency kernel |
|---|---:|---:|
| Rebuilt baseline | 37.639 [37.129, 39.056] | 93.570 [93.088, 93.959] |
| Rebuilt candidate | 12.055 [11.828, 12.227] | 37.046 [36.743, 38.045] |

Throughput speedup: **3.12x**. Dependency-kernel speedup: **2.53x**. Each module has five warmups and 15 measured rounds per domain/mode/implementation; both run sequentially without concurrent compilation. [Per-round data and summaries](../../benchmarks/results/raw-logs/target-scope/std/) retain checksums and all input domains. The scoped ordinary-std export executes 151,083 exact input pairs, agrees with direct candidate output bits except unspecified NaN payloads, and passes independent 256-bit MPFR checking with maximum observed error 0.5055620758593419 ULP. This is actual rebuilt std, not an application-level alias.

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

The sysroot copy must retain its own module list: a checkout's complete math/mod.rs can refer to modules absent from that sysroot. The preparation script modifies only the helper, pow selector and pow-specific source. No unresolved Cargo restriction remains for this experiment.

## Real marginal size

All fixtures call ordinary std and differ only by the paired rebuilt sysroot. Release opt-level 3, fat LTO, one codegen unit, abort, symbols stripped. Compression is `gzip -9 -n` and `brotli -q 11`; [size.csv](size.csv) also records raw/gzip/Brotli for `wasm-opt --all-features -O3` and `-Oz` (54 combinations total).

| Fixture | Raw bytes, before → after (delta) | gzip bytes | Brotli bytes |
|---|---:|---:|---:|
| minimal | 2524 → 6686 (+4162) | 1444 → 4895 (+3451) | 1387 → 4665 (+3278) |
| medium | 16565 → 20725 (+4160) | 8199 → 11693 (+3494) | 7489 → 10740 (+3251) |
| application | 128761 → 132985 (+4224) | 57393 → 60944 (+3551) | 49337 → 52609 (+3272) |

Minimal exports only the pow interface. Medium also links exp, exp2, ln, log2, sin_cos and atan2. The 129 KB representative application performs JSON parsing, cash-flow discounting/duration calculations, and JSON serialization, with runtime-supplied rates/periods and a consumed output hash. It is a computational fixture, not random padding or a production application. Executable checks exercise all 18 baseline/candidate/optimizer modules and verify no host math imports. The [retained artifacts and build logs](../../benchmarks/results/raw-logs/target-scope/size/) correspond to this scoped source; the initial unscoped artifacts remain separately archived under `results/wasm/`. Results cannot be extrapolated to every large WASM product; no production application was measured.

The candidate contains a 3,072-byte logarithm table and a 2,048-byte exponential table. Each entire table occurs exactly once in each unoptimized candidate fixture ([evidence](../../benchmarks/results/raw-logs/target-scope/size/artifacts.json)); baseline fixtures contain neither. Byte-search counts are not used for optimized files because Binaryen can split/rewrite data segments. Other existing libm exp/log algorithms use different tables or polynomial data, so adding them does not produce genuine table sharing. The measured gzip marginal cost is slightly larger in the application than in the minimal module, while Brotli's is smaller; a bigger app does not guarantee a smaller compressed delta.

## Decision

This supports a narrowly scoped f64 pow proposal: the A and B speedups are measured, permissive provenance is retained, and finite MPFR accuracy improves in the tested sample. Review still needs to weigh approximately 3.2–3.6 KB extra compressed application code, table maintenance, input-dependent performance and rounding-mode/fenv expectations. Default/native CPU execution on four hosted targets, Rust 1.67 library-only builds and 11-target selection checks are recorded in the [hardware report](../../benchmarks/reports/architecture-comparison.md). The portable non-FMA path avoids target-specific intrinsics and builds on a non-WASM no_std fallback. No native std speedup is claimed. Other functions have not been ranked because the requested patch scope is pow.
