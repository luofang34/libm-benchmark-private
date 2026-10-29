# Pow hardware validation

## STM32H743: hardware FP64

The connected device completed 420 timed batches (seven input distributions, two modes, two implementations, 15 paired rounds) and a separate 448-pair accuracy pass. Its self-reported Flash SHA-256 matches the audited binary: `b6015f7c4617b94d2ac18e1bef77ceeb0b05e369be6aa6c142a81a55ac280b2a`. Firmware source commit: `a94cb7e3e59da22ea9e4bd9d45c0184af7b8427e`. Baseline source: `6bc104a50f83cb205790c61c5d33508046f5fad3`. The candidate is the non-FMA Arm pow port in this repository.

USB DFU identified serial `200364500000`; the running firmware reported UID `430030001051333336393535`, silicon ID `0x20036450`, 2048 KiB Flash, and nominal 200 MHz. The PCB model is unreported. Build settings use `thumbv7em-none-eabihf`, `target-cpu=cortex-m7`, hard-float ABI, Rust 1.99.0 and LLVM 23.1.1. Linked disassembly retains calls to both pow implementations and hardware FP64 instructions, without FP64 software arithmetic helpers or FMA libcalls.

The measured CCR is `0x60200`: **I-cache is enabled and D-cache is disabled**. Cache enable bits are 17 and 16 respectively, as defined by [Arm CMSIS](https://github.com/ARM-software/CMSIS_5/blob/develop/CMSIS/Core/Include/core_cm7.h). The firmware explicitly enables I-cache and preserves D-cache state inherited from the bootloader. Code and tables execute/read from internal Flash; the stack uses AXI SRAM. Interrupts are disabled and USB is polled outside timed batches. DWT provides 32-bit core-cycle intervals with wrapping subtraction; the longest recorded batch is far below one wrap. Nanoseconds in the CSV use the configured 200 MHz clock, without independent oscillator calibration.

| Distribution | Baseline throughput cycles/op | Candidate throughput cycles/op | Paired throughput speedup | Paired dependency speedup |
|---|---:|---:|---:|---:|
| Ordinary positive | 864.45 | 737.00 | 1.173× | 1.174× |
| Near one, large exponent | 638.55 | 704.52 | 0.906× | 0.921× |
| Small/large magnitudes | 864.31 | 752.44 | 1.149× | 1.136× |
| Negative, integer exponent | 805.39 | 756.58 | 1.065× | 1.078× |
| Subnormal | 800.23 | 818.63 | 0.977× | 0.989× |
| Overflow/underflow edge | 746.03 | 809.63 | 0.922× | 0.910× |
| Special values | 200.00 | 286.63 | 0.698× | 0.768× |

Speedup is the median of paired baseline/candidate ratios; a value below one is a regression. Ordinary-positive throughput p10–p90 is 864.20–864.62 cycles/op for baseline and 736.80–737.41 for candidate. Full distributions and checksums are in [hardware.csv](../results/hardware.csv), with each trial in [the raw capture](../results/raw-logs/stm32h743/timing.csv). Dependency measurements include feedback overhead; output-dependent inputs can differ between implementations. These are warmed batches within one boot, not independent reboot trials.

The candidate's observed maximum error is `0.4999999999955404` ULP versus baseline `0.6710095080248282` ULP using MPFR at 256-bit precision. There were no NaN/infinity classification or signed-zero mismatches. The [accuracy results](../results/raw-logs/stm32h743/accuracy.csv) include ULP bins and worst inputs. This 448-pair hardware corpus is a targeted smoke test, not a global error bound or a replacement for the larger [native/WASM accuracy evaluation](../../experiments/pow/accuracy.md).

## H743 replacement size

Two separately linked single-algorithm compute fixtures use identical flags, runtime, input corpus and loop. Disassembly confirms each retains only its selected implementation. These are offline size fixtures, not flashed measurement images.

| Section | Baseline bytes | Candidate bytes | Replacement delta |
|---|---:|---:|---:|
| `.text` | 3,692 | 2,836 | −856 |
| `.rodata` | 7,472 | 12,288 | +4,816 |
| Flash image including vectors/alignment | 11,832 | 15,792 | **+3,960** |
| Static `.data + .bss` | 0 | 0 | 0 |

Constants reside in Flash. The fixtures include only pow, so they do not establish sharing with exp/log. Stack usage is unmeasured. The dual-algorithm USB firmware occupies 69,100 Flash bytes and 4 bytes of static RAM, **excluding** its 128 KiB stack-resident telemetry buffer and other stack frames. Static RAM must not be interpreted as peak RAM. [memory.csv](../results/memory.csv) and [linked artifacts](../results/raw-logs/stm32h743/size/manifest.json) preserve the exact scope.

## STM32F411: hardware FP32 with software FP64

The F411 completed the same 420 timed batches and 448-pair accuracy pass. DFU serial is `368C358D3133`, runtime UID `550055000951333138353736`, silicon ID `0x10006431`, and Flash capacity 512 KiB. The PCB model is unreported. Firmware SHA-256 is `2bb4472d31e4826ebe04dfc3563cc8a502b25cf6c301360b5f7d3926291c297b`, from source `585febd52469c7c687939a839c7090b5b93fd6c6`. The raw [capture and identity](../results/raw-logs/stm32f411/device.json) match the archived Flash image.

Build settings are `thumbv7em-none-eabihf`, `target-cpu=cortex-m4`, hard-float ABI, Rust 1.99.0 and LLVM 23.1.1. MVFR0 is `0x10110021`; disassembly confirms FP32 arithmetic and software FP64 helper calls, with no FP64 hardware arithmetic or FMA libcall. FPSCR is `0x10`, with default rounding and no flush-to-zero/default-NaN mode. Flash ACR is `0x701` (prefetch and instruction/data caches enabled, one wait state); core CCR is `0x200`.

TIM11's HSI-based HSE estimate is 25,647,183 Hz, rounded to 26 MHz for PLL configuration. This is a startup frequency estimate, not an independently calibrated crystal measurement. The core clock and converted nanoseconds use nominal 48 MHz; **cycles are the primary result**. No external frequency measurement was performed. Interrupts are disabled, code/tables reside in Flash, and USB traffic stays outside timed intervals.

| Distribution | Baseline throughput cycles/op | Candidate throughput cycles/op | Paired throughput speedup | Paired dependency speedup |
|---|---:|---:|---:|---:|
| Ordinary positive | 13,480.98 | 9,925.28 | 1.358× | 1.359× |
| Near one, large exponent | 9,218.67 | 9,177.61 | 1.004× | 1.004× |
| Small/large magnitudes | 13,542.89 | 10,098.22 | 1.341× | 1.341× |
| Negative, integer exponent | 11,987.61 | 9,580.50 | 1.251× | 1.251× |
| Subnormal | 12,290.86 | 10,779.80 | 1.140× | 1.141× |
| Overflow/underflow edge | 10,501.61 | 10,063.41 | 1.044× | 1.044× |
| Special values | 974.05 | 1,508.30 | 0.646× | 0.588× |

Ordinary-positive throughput p10–p90 endpoints both equal 13,480.984375 cycles/op for baseline and 9,925.28125 for candidate in these deterministic, interrupt-disabled batches. This is one boot with five warmups and 15 paired rounds, not evidence of zero variability across reboots or boards. Exact checksums and every round are retained in [timing.csv](../results/raw-logs/stm32f411/timing.csv).

The 256-bit MPFR check observes the same maxima as H743: candidate `0.4999999999955404` ULP, baseline `0.6710095080248282` ULP, and zero classification/signed-zero mismatches. All finite candidate samples are within 0.5 ULP in this corpus. The targeted hardware sample does not establish a global error bound.

## F411 replacement size

Identically configured single-algorithm compute fixtures retain only their selected pow implementation and required software FP64 helpers. They were built offline, not flashed.

| Section | Baseline bytes | Candidate bytes | Replacement delta |
|---|---:|---:|---:|
| `.text` | 7,984 | 6,792 | −1,192 |
| `.rodata` | 7,472 | 12,288 | +4,816 |
| Flash image including vectors/alignment | 15,864 | 19,488 | **+3,624** |
| Static `.data + .bss` | 0 | 0 | 0 |

The dual-algorithm USB measurement firmware is 73,476 Flash bytes with 4 static RAM bytes, excluding its 80 KiB stack-resident payload and other frames. Peak stack is unmeasured. The isolated fixtures establish neither large-application marginal cost nor exp/log table sharing. Exact artifacts are in the [size manifest](../results/raw-logs/stm32f411/size/manifest.json).

## Interpretation and remaining hardware

The approximately 3× WASM improvement does not generalize to these MCUs. Ordinary-positive throughput gains are 1.173× on H743 and 1.358× on F411. H743 near-one inputs regress about 10%; the special-value mixture takes about 43% longer on H743 and 55% longer on F411. This evidence does not yet justify a universal replacement for all embedded targets. RP2350 Arm/Hazard3 comparisons and a separate DCP implementation and accuracy result remain unmeasured.

Nine target profiles pass compilation and instruction/helper inspection in [codegen.json](../results/codegen/codegen.json). Those unlinked objects are not board measurements. Unconnected boards remain explicitly blocked in [profiles.json](../boards/profiles.json). K230 CPU0/CPU1 and ATmega328P are deferred and have not been built or flashed. No upstream PR has been opened.

## Hosted hardware comparison

The same 448-pair corpus and shared kernel ran on three hosted configurations. Each used Rust 1.99.0, LLVM 23.1.1, `target-cpu=native`, five warmup rounds and 15 paired rounds. Source commit: `a177542435f4aab8a8bc1fe235604537193094f7`. The [manual Linux workflow](https://github.com/luofang34/libm-benchmark-private/actions/runs/40862882436) completed successfully on both architectures; downloaded artifact SHA-256 values were checked against GitHub's recorded digests.

| Observed host identity / LLVM CPU | Positive baseline ns/op | Positive candidate ns/op | Throughput speedup (p10–p90) | Dependency speedup |
|---|---:|---:|---:|---:|
| Apple M3 Max / `apple-m3` | 32.087 | 9.568 | 3.349× (3.121–3.482) | 2.454× |
| AMD EPYC 9V74 VM / `znver4` | 33.105 | 13.166 | 2.514× (2.500–2.543) | 2.331× |
| Arm VM, implementer `0x41`, part `0xd49` / `neoverse-n2` | 46.001 | 20.462 | 2.247× (2.244–2.251) | 2.212× |

The Arm VM does not expose a SoC product name; raw `/proc/cpuinfo` and compiler CPU/features are retained instead of inferring one. Hosts use OS scheduling without core affinity; no host cycle counts are inferred from nominal frequencies. Each timing population stays separate in [hosted.csv](../results/hosted.csv). Single workflow runs do not establish long-term GitHub runner stability.

All three hosts passed the 256-bit MPFR check with candidate observed maximum `0.4999999999955404` ULP, baseline `0.6710095080248282` ULP, and zero classification/signed-zero mismatches. Full raw inputs, outputs, per-domain bins and environments are in `results/raw-logs/`. These samples remain targeted evidence rather than a whole-domain worst-case bound.

One quiet-NaN/signaling-NaN input pair has a different NaN payload on x86-64 versus Arm. Both implementations agree within each architecture, and both results classify as NaN. Cross-platform bitwise identity of NaN payloads is not claimed.

## Verification and reproduction

Run the commands in the component [README](../README.md). The archived H743 capture can be revalidated with:

```sh
python3 benchmarks/scripts/ingest_h743.py benchmarks/results/raw-logs/stm32h743 \
  --firmware benchmarks/results/raw-logs/stm32h743/firmware
```

The DFU log records successful erase/download followed by an error while requesting departure from DFU (exit 74). USB CDC subsequently enumerated and returned the exact expected Flash hash and complete result payload; those observations establish successful execution. Existing firmware was overwritten with explicit authorization and no backup was retained.

For F411, both DFU downloads exited successfully, but departure did not establish CDC. A BOOT0-released power cycle produced CDC and the complete matching capture. The successful image explicitly initializes startup state; the experiment does not isolate which bootloader state caused the departure failure. Revalidate without hardware using `python3 benchmarks/scripts/ingest_f411.py benchmarks/results/raw-logs/stm32f411 --firmware benchmarks/results/raw-logs/stm32f411/firmware`. No original Flash backup was retained.

The shared benchmark's four Rust tests, 16 Python tests, strict Clippy/doc checks and H743/F411 preflights pass. The repository-wide tests (2,198 passed), release, format and API gates pass using nightly `41089d07a`; the API script also requires `RUSTUP_TOOLCHAIN=nightly`. Stable cannot compile the root compiler-builtins workspace's nightly features. Strict repository-wide Clippy and documentation gates fail on existing upstream documentation issues (including 105 compiler-builtins Clippy errors for missing safety sections and other documentation issues). Those failures are not reported as successful CI.
