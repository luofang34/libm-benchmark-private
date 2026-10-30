# libm: use Arm's table-based f64 pow on measured targets

<!-- Private review draft. Do not submit upstream until the repository owner
approves. The proposed upstream diff is libm-pow-arm.patch, not this experiment
branch. Before submission, make the reproducible harness and referenced evidence
available to reviewers with the owner's approval; private links alone are not
a public reproduction path. exp/exp2 experiments are excluded from this PR. -->

This changes double-precision `libm::pow` to Arm's scalar table-based algorithm
on five measured targets. In a paired Rust sysroot rebuild, ordinary
`f64::powf` on `wasm32-unknown-unknown` improves from 37.64 to 12.05 ns/call
for independent normal-positive inputs (3.12×), and from 93.57 to 37.05 ns/call
for a dependent kernel (2.53×). The tradeoff is about 3.2–3.6 KB of additional
compressed WASM in the measured applications. Other input distributions and
MCU results below explain the restricted target selection.

## Change and scope

The port uses the non-FMA path of
[Arm optimized-routines `math/pow.c`](https://github.com/ARM-software/optimized-routines/blob/2ee4b0d45680a9880412c1d186224b08652c35f6/math/pow.c).
It computes a compensated logarithm, multiplies by the exponent using split
binary64 values, and reconstructs the result with a table-based exponential.
Copyright and MIT permission notices are retained. The coefficients and all
640 table words were checked against the compiled Arm C data. No Rust code from
the separately benchmarked `petir` crate is incorporated.

Compile-time selection enables the port for:

| Target | Required target feature |
|---|---|
| `wasm32-unknown-unknown` | Default scalar WASM FP64 |
| `aarch64-apple-darwin` | `neon` |
| `aarch64-unknown-linux-gnu` | `neon` |
| `x86_64-unknown-linux-gnu` | `sse2` |
| `x86_64-pc-windows-msvc` | `sse2` |

The fdlibm implementation is retained for other targets, including bare-metal
MCUs, musl and WASI. A target-selection check covers five candidate and eight
fallback configurations. This is an evidence-based initial allowlist, not a
claim that other platforms cannot benefit.

The seven-file math diff changes only f64 `pow`, its internal helpers/data,
target selection and regression tests. It adds no public API, runtime dispatch,
production dependency, unsafe code or FMA requirement. f32 `powf`, public `exp`
and `exp2`, and the `std`/compiler-builtins symbol-availability policy are
unchanged. Regression tests cover signed zero, signaling-NaN identities,
subnormals, range boundaries and a difficult logarithm-reduction case.

## Performance

Measurements distinguish direct calls to this crate from ordinary Rust `std`.
Rust `f64::powf` corresponds to the double-precision `llvm.pow.f64`/C `pow`
operation, not C `float powf`.

For the WASM experiment, both baseline and candidate sysroots were rebuilt with
nightly `-Z build-std`. The compiler-builtins source actually consumed by the
build and the resulting `pow` symbol were checked. An application-level
`[patch.crates-io]` was not used as a substitute for rebuilding the sysroot.

On the measured native OS targets, ordinary `std::f64::powf` continues to use
the platform math library. The native table below measures **direct `libm`**
calls; it is not evidence of a native `std` speedup. An executed macOS probe
resolved `_pow` to `libsystem_m.dylib`. The platform implementation was already
competitive with this port.

### Rebuilt WASM std: all measured input domains

Apple M3 Max, Node 26.12.1 / V8 14.6.202.34-node.40. Entries are median
ns/call [p10, p90]; speedup is baseline median / candidate median.

| Domain | Mode | Baseline | Candidate | Speedup |
|---|---|---:|---:|---:|
| positive | throughput | 37.64 [37.13, 39.06] | 12.05 [11.83, 12.23] | 3.12× |
| positive | dependency | 93.57 [93.09, 93.96] | 37.05 [36.74, 38.04] | 2.53× |
| near_one | throughput | 23.65 [23.39, 23.76] | 11.91 [11.62, 12.15] | 1.99× |
| near_one | dependency | 70.32 [70.18, 70.72] | 37.39 [35.92, 37.81] | 1.88× |
| negative_integer | throughput | 33.15 [32.90, 33.93] | 12.86 [12.66, 13.20] | 2.58× |
| negative_integer | dependency | 81.07 [80.19, 81.24] | 34.99 [34.27, 36.70] | 2.32× |
| subnormal | throughput | 37.48 [35.42, 39.63] | 22.92 [20.25, 24.46] | 1.64× |
| subnormal | dependency | 78.01 [75.61, 79.50] | 39.96 [39.63, 40.22] | 1.95× |
| range_edge | throughput | 35.12 [34.66, 36.00] | 22.38 [22.06, 22.69] | 1.57× |
| range_edge | dependency | 60.12 [59.36, 61.14] | 42.76 [42.37, 43.48] | 1.41× |
| special | throughput | 5.30 [5.03, 5.48] | 4.56 [4.44, 4.70] | 1.16× |
| special | dependency | 5.41 [5.16, 5.68] | 5.55 [5.46, 5.66] | 0.97× |

The special-value dependent kernel is 2.6% slower in this capture. Its
distributions overlap, and result-dependent feedback can change which special
input comes next; this is not evidence of uniform improvement. The near-one,
subnormal and overflow/underflow-edge cases also do not show a universal 3× gain.

Inputs are prepared before timing. Each round performs 524,288 calls inside
WASM, using 16,384 input pairs and 32 passes. There are five warmup rounds and
15 measured rounds per domain/mode, with rotating implementation order.
Independent-input kernels use four checksum accumulators; dependent kernels
feed output bits into the next input and include that feedback overhead.
All outputs are consumed. Non-inlined wrappers and input barriers prevent
constant folding and loop-invariant hoisting. JS crosses the boundary only
for the batch, not for each math operation. No PRNG work is timed.

These are dependent **kernel** times, not isolated instruction latencies.
No overhead subtraction or outlier trimming is applied. Checksums and all
per-round observations are retained in the evidence.

### Hosted native: direct libm calls

Normal-positive inputs; baseline/candidate are median ns/call. Speedups are
the median of paired round ratios [p10, p90], so they need not equal the ratio
of the two displayed medians. Default and host-native compiler settings are
separate observations.

| Host / OS | Target CPU | Baseline | Candidate | Throughput speedup [p10, p90] | Dependent speedup |
|---|---|---:|---:|---:|---:|
| Neoverse N2 VM / GNU Linux | generic | 46.997 | 19.176 | 2.451 [2.448, 2.452] | 2.464× |
| Neoverse N2 VM / GNU Linux | neoverse-n2 | 46.099 | 20.449 | 2.253 [2.249, 2.257] | 2.221× |
| EPYC 9V45 / GNU Linux | x86-64 | 27.035 | 10.920 | 2.481 [2.446, 2.532] | 2.261× |
| EPYC 9V45 / GNU Linux | znver5 | 25.807 | 10.357 | 2.469 [2.449, 2.506] | 2.263× |
| Apple M3 Max / macOS | apple-m1 | 31.826 | 9.673 | 3.293 [3.248, 3.338] | 2.468× |
| Apple M3 Max / macOS | apple-m3 | 31.669 | 9.620 | 3.292 [3.232, 3.345] | 2.442× |
| EPYC 7763 / Windows Server 2025 | x86-64 | 49.075 | 17.933 | 2.735 [2.638, 2.827] | 2.303× |
| EPYC 7763 / Windows Server 2025 | znver3 | 47.870 | 16.586 | 2.923 [2.484, 3.286] | 2.280× |

All seven distributions in both modes improved in these eight configurations;
the smallest paired median gain was 1.053× (macOS native-CPU range-edge dependent
kernel). Each configuration is one OS-scheduled, unpinned capture, not a
cross-machine confidence interval. Windows performance comes from the MSVC
Rust executable; a separate MPFR checker does not determine its code generation.

### MCU evidence and why these targets keep the fallback

The candidate was explicitly forced on MCU experiment builds. The proposed
library selector does **not** enable it there. Speedups below are paired median
baseline/candidate ratios: values below 1 mean a slowdown. `T` denotes
independent throughput and `D` the dependent kernel. Flash deltas come from
separate single-implementation linked fixtures, not the larger telemetry image.

| Configuration | FP capability used | Positive T / D | Special T / D | Linked Flash delta |
|---|---|---:|---:|---:|
| STM32H743 / Cortex-M7 | hardware FP32/64 | 1.173× / 1.174× | 0.698× / 0.768× | +3,960 B |
| STM32F411 / Cortex-M4F | hardware FP32; software FP64 | 1.358× / 1.359× | 0.646× / 0.588× | +3,624 B |
| RP2040 / Cortex-M0+ | software FP32/64 | 1.547× / 1.569× | 0.708× / 0.669× | +3,400 B |
| RP2350 / Cortex-M33 | hardware FP32; software FP64 | 1.349× / 1.357× | 0.658× / 0.595× | +3,648 B |
| RP2350 / Hazard3 | software FP32/64 | 1.348× / 1.366× | 0.637× / 0.601× | +3,584 B |
| ESP32-C6 / RISC-V | ROM software FP32/64 | 1.407× / 1.407× | 0.720× / 0.784× | +3,520 B |
| RP2350 / Cortex-M33 + DCP **accuracy failed** | hardware FP32; DCP-assisted FP64 | 1.908× / 1.894× | 0.605× / 0.529× | +3,616 B |

The finite normal-positive path improves even with software FP64, but the
special-value paths are slower and the tables add roughly 3.4–4.0 KB of linked
Flash. The H743 hardware-FP64 result also regresses for near-one (0.906×),
subnormal (0.977×) and range-edge (0.922×) throughput. Hardware FP64 alone is
therefore insufficient justification for enabling this algorithm on all MCUs.
The fallback here is compile-time target selection; the port does not dispatch
special values back to a second pow implementation at runtime.

The RP2350 DCP add/multiply configuration failed accuracy checks for **both**
algorithms: 45 of 64 subnormal cases exceeded 2 ULP; the candidate returned zero
for `pow(min_subnormal, 1)`. Its timing is retained only as a diagnostic and is
not an accepted IEEE-accuracy performance result. This identifies a problem
with the tested arithmetic/runtime configuration, not a candidate-only failure.
The other six configurations passed their 448-pair 256-bit MPFR corpus.

MCU captures use five warmups and 15 paired rounds from one boot. CPU, features,
float ABI, clock, runtime, cache/Flash configuration, cycles, bytes and accuracy
status are recorded separately rather than inferred from the target triple.
The RP2040 capture uses cached single-bit XIP; the C6 uses ROM software FP
helpers. These results do not establish performance for all implementations of
the same core. K230, ATmega and physical Xtensa hardware are not covered.

### Upstream instruction-count benchmarks

The official `icount` and `mem_icount` benchmarks passed 2,862 comparisons with
zero flagged regressions across three targets and `arch` enabled/disabled.
The f64 pow counts below are instructions for the **complete benchmark**,
not hardware cycles or ns/call:

| Target / runner | `arch` | Baseline | Candidate | Reduction |
|---|---|---:|---:|---:|
| AArch64 GNU/Linux, Neoverse N2 | disabled | 54,512 | 23,301 | 57.26% |
| AArch64 GNU/Linux, Neoverse N2 | enabled | 54,104 | 23,301 | 56.93% |
| x86-64 GNU/Linux, EPYC 7763 | either | 56,675 | 25,022 | 55.85% |
| i686 GNU/Linux, EPYC 7763 | either | 66,825 | 66,825 | 0% (fallback) |

These use independent baseline/candidate builds. An initial local attempt that
reused a shared build directory is excluded, as is a walltime run overlapped by
compilation. The valid instruction-count results are separate from the custom
input-distribution timing results above.

## Linked size and table ownership

Paired sysroots and identical build settings measure replacement within the
same application. The minimal fixture exports only ordinary `std::powf`; the
medium fixture uses several math functions. The larger fixture performs JSON
parsing, cash-flow discounting/duration calculation and serialization, consuming
runtime inputs and returning a result hash. It is representative computation,
not a production application or random padding.

| Fixture | Raw WASM baseline → candidate | gzip baseline → candidate | Brotli baseline → candidate |
|---|---:|---:|---:|
| Single function | 2,524 → 6,686 (+4,162) | 1,444 → 4,895 (+3,451) | 1,387 → 4,665 (+3,278) |
| Multiple math functions | 16,565 → 20,725 (+4,160) | 8,199 → 11,693 (+3,494) | 7,489 → 10,740 (+3,251) |
| Representative application | 128,761 → 132,985 (+4,224) | 57,393 → 60,944 (+3,551) | 49,337 → 52,609 (+3,272) |

Compression is `gzip -9 -n` and Brotli quality 11. Binaryen 128 `-O3` and `-Oz`
were also measured on both sides:

| Fixture | Optimization | Δ raw | Δ gzip | Δ Brotli |
|---|---|---:|---:|---:|
| minimal | `-O3` | +4,304 | +3,470 | +3,321 |
| minimal | `-Oz` | +4,302 | +3,463 | +3,274 |
| medium | `-O3` | +4,308 | +3,474 | +3,290 |
| medium | `-Oz` | +4,310 | +3,471 | +3,275 |
| application | `-O3` | +4,356 | +3,500 | +3,229 |
| application | `-Oz` | +4,358 | +3,485 | +3,331 |

These are actual paired marginal sizes, not differences between independently
compressed function blobs. The larger fixture does not consistently compress
the added algorithm better: its unoptimized gzip increment is larger than the
minimal fixture's increment.

Each unoptimized linked candidate contains one 3,072-byte logarithm table and
one 2,048-byte exponential table. Public `exp`/`exp2` still use their existing
implementations; this PR does **not** claim they share the new table. A separate
follow-up could move the exponential table to a shared internal module and
have `pow`, `exp` and `exp2` all reference one static definition. The logarithm
table remains specific to pow. Such a follow-up needs independent accuracy and
performance testing, final-link checks with and without LTO, and paired
application-size measurements. No future sharing or compression saving is
included in the benefit claimed for this PR, and that work is not a dependency
of this change.

## Accuracy and compatibility

A separate 151,083-pair corpus combines random, boundary and adversarial inputs
and compares actual native/WASM outputs with 256-bit MPFR 4.2.2 references.
Observed maximum errors were 0.7858855122 ULP for the baseline and
0.5055620759 ULP for the candidate. Candidate finite-result bins were 8,734
exact, 122,196 in (0, 0.5] ULP and 107 in (0.5, 1] ULP; IEEE classification and
signed-zero checks found no mismatches. This corpus also passed on all eight
hosted native configurations. These are repeated executions of the same corpus,
not eight independent random searches or a proof of a global error bound.

The unmodified upstream extensive-test invocation for pow additionally checked
17,179,869,184 spaced input pairs with zero failures, without reducing the
iteration count. That harness uses a correctly rounded **53-bit** MPFR result
and ULP-distance/classification checks. It is distinct from the 256-bit
fractional-ULP analysis and also does not prove a full-domain worst-case bound.

Three signaling-NaN identity cases intentionally differ from the Arm C
reference: `1^sNaN` and `sNaN^(±0)` return 1, preserving Rust libm behavior.
NaN payload equality is not required. Testing assumes round-to-nearest; this
port does not add errno/floating-exception behavior or a guarantee for other
rounding modes. The Arm algorithm's error analysis is useful context, not a
substitute for validating this Rust transcription.

## Validation and reproduction

Validation applies to the seven-file math source, whose hashes were checked
across the builds. The experiment harness and private CI workflows are outside
the proposed upstream patch.

- The three test groups in `CONTRIBUTING.md` passed: basic, feature-enabled,
  and release-checked MPFR/musl (715, 869 and 2,534 tests respectively).
- Target CI checks passed for 25 configurations: 20 execute tests and five
  follow upstream's build-only path. These results aggregate successful jobs
  from two runs, not one entirely successful matrix run. Extra s390x GNU and
  powerpc64 musl checks were cross-builds only; their dedicated upstream runners
  were not replicated.
- Symbol checks covered 28 configurations on six targets. Twelve intrinsic-link
  configurations covered macOS and WASM, including LTO. The standalone WASM pow
  probe had no imports, contained one copy of each table, and matched all 151,083
  reference-output cases. No unintended math libcall or software FMA was found.
- Miri passed its three official target configurations and the macOS pow tests.
  No-panic checks passed on macOS and WASM. Rust 1.67 production-source builds
  passed on macOS, WASM and a Cortex-M fallback. The manifest/CI MSRV is 1.67;
  the README's older 1.63 statement was not validated.
- Formatting, tests and release builds passed. Strict whole-workspace Clippy
  and missing-docs checks still report reproduced upstream diagnostics outside
  this patch; they are not reported as passing. In the isolated libm doc
  comparison, baseline and candidate emitted the same 20 diagnostics.

The upstream test commands are:

```sh
cargo test --workspace --no-default-features
cargo test --workspace --no-default-features \
  --features arch,unstable-float,unstable-intrinsics,mem
cargo test --workspace --no-default-features \
  --features arch,unstable-float,unstable-intrinsics,mem,build-mpfr,build-musl \
  --profile release-checked
TO_TEST=pow bash ci/run-extensive.sh
cargo bench --no-default-features \
  --features arch,unstable-float,unstable-intrinsics,mem,icount \
  --bench icount --bench mem_icount
```

Use the recorded nightly for unstable features; musl/MPFR tests and instruction
counts require the dependencies and platform restrictions described in
`CONTRIBUTING.md`. The custom harness also requires Node, Clang, MPFR/GMP,
Binaryen and Brotli. Its source and logs retain the exact commands, datasets,
CPU features, checksums and artifact hashes.

<details>
<summary>Initial direct-call comparison and native system-math control</summary>

This is a separate exploratory capture, retained rather than blended with the
scoped-source results. Normal-positive inputs, median ns/call [p10, p90]:

| Runtime | Implementation | Independent throughput | Dependent kernel |
|---|---|---:|---:|
| Native macOS | Baseline libm | 46.300 [35.833, 63.381] | 91.634 [90.786, 99.866] |
| Native macOS | petir | 9.970 [9.400, 13.704] | 37.164 [36.711, 42.982] |
| Native macOS | std (system math) | 8.352 [7.639, 15.320] | 33.303 [32.507, 34.672] |
| Native macOS | Arm port | 11.260 [9.724, 20.482] | 37.229 [36.880, 40.774] |
| WASM | Baseline libm | 36.824 [36.154, 37.653] | 109.362 [98.141, 153.726] |
| WASM | petir | 13.130 [12.824, 13.516] | 46.673 [41.421, 61.638] |
| WASM | std (unpatched) | 38.005 [37.069, 38.558] | 115.072 [99.516, 142.407] |
| WASM | Arm port | 12.061 [11.671, 12.382] | 44.598 [38.200, 59.795] |

The direct WASM port is 3.05× faster than baseline libm here. This alone was not
used to claim patched-std performance; the paired sysroot experiment above
supplies that evidence. The broad intervals in several initial captures should
also discourage comparing small differences between these implementations.

A corrected C++ `double pow` benchmark measured 8.862 ns/call over 15 rounds.
Disassembly retained the call through the non-inlined wrapper to `_pow`;
`-fno-builtin-pow`, precomputed inputs and a consumed checksum prevent the
earlier elimination problem. The earlier 0.276 ns/call C++ figure is excluded.
No claim is made that this port improves the already optimized native OS math
library.

</details>

<details>
<summary>Source identities and private evidence index for draft review</summary>

| Item | Identity |
|---|---|
| Upstream baseline | `6bc104a50f83cb205790c61c5d33508046f5fad3` |
| Tested math revision | `f39774d821b2bbc19c98dca827678fdce636d075` |
| Arm reference | `2ee4b0d45680a9880412c1d186224b08652c35f6` |
| Standalone seven-file patch SHA-256 | `47a4a9732d78d2d744bf9d48d10c3159f001fe10d76cd572c5d89c41537fc5e6` |
| Rust stable / LLVM | 1.99.0 `b940084d7eb6a299eb4bfeb8e34901bc051e7ac4` / 23.1.1 |
| Sysroot and upstream-CI nightly / LLVM | 1.101.0 `41089d07a0a2afc16adfe28a760d94d73d7298a4` / 23.1.4 |
| Nightly compiler-builtins source tree | `17a9e503efa529a41236ef11ef58108f840ccc72` |
| Packages in checkout | libm 0.2.16; compiler_builtins 0.1.160 |
| macOS machine | Apple M3 Max; macOS 27.0 build 26A5368g |
| Clang | Apple 21.0.0 `clang-2100.4.1.1` |
| Node / V8 | 26.12.1 / 14.6.202.34-node.40 |
| MPFR / Binaryen / Brotli | 4.2.2 / 128 / 1.2.1 |

The nightly sysroot source is checked independently of the repository package
version; equal version strings do not imply equal source trees.

- [Seven-file patch](libm-pow-arm.patch) and [table verifier](check_tables.py).
- [Initial harness, method and environment](BENCHMARK.md),
  [complete direct-call performance CSV](performance.csv), and
  [std integration reproduction](STD_INTEGRATION.md).
- [Scoped rebuilt-std CSV](../../benchmarks/results/raw-logs/target-scope/std/performance.csv)
  and [paired size CSV](../../benchmarks/results/raw-logs/target-scope/size/size.csv).
- [Hosted CSV](../../benchmarks/results/hosted.csv),
  [MCU CSV](../../benchmarks/results/hardware.csv), and
  [MCU linked-memory CSV](../../benchmarks/results/memory.csv).
  Use the scoped default/native populations for the hosted table; the CSV
  deliberately retains earlier captures as separate run IDs.
- [256-bit MPFR corpus and outputs](accuracy.md). Its older validation-summary
  paragraphs are superseded by the contribution-validation evidence below;
  the corpus results themselves are unchanged.
- [Contribution validation and limits](../../benchmarks/results/raw-logs/contribution-validation/summary.json),
  [instruction counts](../../benchmarks/results/raw-logs/contribution-validation/icount-results.json),
  and [earlier symbol/link/Miri evidence](../../benchmarks/results/raw-logs/upstream-validation/).

These paths are private review references. The public PR must provide an
owner-approved, accessible reproduction bundle rather than ask reviewers to
trust inaccessible logs. No upstream PR has been opened by preparing this draft.

</details>
