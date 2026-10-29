# pow accuracy evidence

Native MPFR **4.2.2**, **256-bit** precision, round-to-nearest, evaluates **151,083 input pairs**. Each candidate is executed in Node/V8 WASM and its output bits are checked by the native MPFR program. Input and output use integer bit-pattern exports (`pow_bits`) to preserve signed zeros and signaling NaNs across the JS boundary. Native Rust candidate results also agree with WASM for all 151,083 inputs, excluding unspecified NaN payload differences.

## Coverage and metric

`accuracy_inputs.py` uses seed 20261029. Seven groups of 20,000 inputs cover normal positive values, near-one with large exponents, negative integer exponents, subnormal bases, overflow/underflow neighborhoods, arbitrary 64-bit inputs, and logarithmically spread bases with scaled exponents. Additional cases straddle all 128 logarithm-table boundaries, probe adjacent representations near one with exponents through 2^64, and form a 20×20 exceptional-value matrix.

ULP error is `abs(result - MPFR_value) / spacing`, computed at MPFR precision. Spacing is the normal reference binade spacing, clamped to 2^-1074 for subnormal/zero results. It is **not** integer distance from a rounded reference; a correctly rounded result can have nearly 0.5 ULP error. Finite values, NaN/infinity classifications, and signed zero are counted separately. Raw values and per-domain histograms are retained; random/adversarial sampling provides evidence, **not a proof of a global worst-case bound**.

## Observed results

The 0–0.5 and 0.5–1 columns exclude exact-zero-error cases. No tested finite result exceeded 1 ULP.

| Implementation | Max observed ULP | Exact | (0,0.5] | (0.5,1] | Classification difference from MPFR | Signed-zero mismatch |
|---|---:|---:|---:|---:|---:|---:|
| libm_old | 0.785885512 | 8734 | 112691 | 9612 | 0 | 0 |
| petir | 0.505562076 | 8731 | 122196 | 107 | 3 | 0 |
| std | 0.785885512 | 8734 | 112691 | 9612 | 0 | 0 |
| arm_patch | 0.505562076 | 8734 | 122196 | 107 | 0 | 0 |
| rebuilt_base | 0.785885512 | 8734 | 112691 | 9612 | 0 | 0 |
| rebuilt_patch | 0.505562076 | 8734 | 122196 | 107 | 0 | 0 |
| arm_c | 0.505562076 | 8731 | 122196 | 107 | 3 | 0 |

[accuracy.csv](results/raw/accuracy.csv) contains the complete per-domain distribution and worst-case inputs, including the subnormal case that reaches 0.5055620758593419 ULP. It is guarded by the new `subnormal_log_reduction` unit test. Regression tests also check negative-zero underflow, minimum-subnormal identity, maximum-finite identity, and NaN identities.

## ARM C and petir comparison

The reference is original ARM C compiled with `HAVE_FAST_FMA=0`, `HAVE_FAST_ROUND=0`, `WANT_ROUNDING=0`, `USE_GLIBC_ABI=0`, `-ffp-contract=off`, and the symbol renamed to arm_pow. Tables/configuration are fixed by the recorded source hashes. Rust uses the same non-FMA arithmetic, a compact table layout, and round-to-nearest special-case handling. No application library call is substituted for the C function.

The candidate and patched std match ARM C bit-for-bit for all non-NaN numerical results except the following **three intentional semantic differences**, which preserve existing Rust libm behavior:

| Inputs | Existing libm / candidate / MPFR | ARM C / petir |
|---|---|---|
| `1.0 ^ signaling_NaN` | 1.0 | NaN |
| `signaling_NaN ^ +0.0` | 1.0 | NaN |
| `signaling_NaN ^ -0.0` | 1.0 | NaN |

The signaling NaN bit pattern is `0x7ff0000000000001`. These are deliberate differences in signaling-NaN handling, not evidence that petir has general finite accuracy failures. NaN payload/sign propagation is not promised or compared. Petir and ARM C otherwise agree on this corpus.

The candidate does not emulate C errno or floating-point exception flags. Only round-to-nearest is evaluated. ARM's upstream error analysis does not automatically constitute a proof for this Rust translation. Non-nearest modes, exhaustive hard-to-round input search, additional soft-float execution targets, and broad upstream CI remain outside this local validation.

## Reproduce and inspect

Run `python3 experiments/pow/run.py` from the repository root. It generates inputs, invokes actual WASM exports, then builds/runs [mpfr_check.c](mpfr_check.c). [MPFR log](results/raw/mpfr.log), [WASM execution log](results/raw/accuracy-wasm.log), [native/WASM comparison](results/raw/native-wasm-equivalence.log), and the raw accuracy CSV contain observed results. The retained compressed binary streams hold original input and output bits; their SHA-256 identities are in the artifact manifest.
