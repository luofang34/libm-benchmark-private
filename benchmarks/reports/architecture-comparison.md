# Pow hardware validation

## STM32H743: hardware FP64

The connected device completed 420 timed batches (seven input distributions, two modes, two implementations, 15 paired rounds) and a separate 448-pair accuracy pass. Its self-reported Flash SHA-256 matches the audited binary: `b6015f7c4617b94d2ac18e1bef77ceeb0b05e369be6aa6c142a81a55ac280b2a`. Firmware source commit: `a94cb7e3e59da22ea9e4bd9d45c0184af7b8427e`. Baseline source: `6bc104a50f83cb205790c61c5d33508046f5fad3`. The candidate is the non-FMA Arm pow port in this repository.

USB DFU identified serial `200364500000`; the running firmware reported UID `430030001051333336393535`, silicon ID `0x20036450`, 2048 KiB Flash, and nominal 200 MHz. The PCB model is unreported. Build settings use `thumbv7em-none-eabihf`, `target-cpu=cortex-m7`, hard-float ABI, Rust 1.99.0 and LLVM 23.1.1. Linked disassembly retains calls to both pow implementations and hardware FP64 instructions, without FP64 software arithmetic helpers or FMA libcalls.

The measured CCR is `0x60200`: **both I-cache and D-cache are enabled**. The firmware explicitly enables I-cache and preserves D-cache state inherited from the bootloader. Code and tables execute/read from internal Flash; the stack uses AXI SRAM. Interrupts are disabled and USB is polled outside timed batches. DWT provides 32-bit core-cycle intervals with wrapping subtraction; the longest recorded batch is far below one wrap. Nanoseconds in the CSV use the configured 200 MHz clock, without independent oscillator calibration.

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

## Interpretation and remaining hardware

The approximately 3× WASM improvement does not generalize to H743: ordinary-positive pow improves about 17%, while near-one inputs regress about 10% and the special-value mixture takes about 43% longer. This evidence does not yet justify a universal replacement for all embedded targets. A decision needs F411's software-FP64 timings, RP2350 Arm/Hazard3 comparisons, and a separate DCP implementation and accuracy result. No DCP measurement has been performed.

Nine target profiles pass compilation and instruction/helper inspection in [codegen.json](../results/codegen/codegen.json). Those unlinked objects are not board measurements. Unconnected boards remain explicitly blocked in [profiles.json](../boards/profiles.json). K230 CPU0/CPU1 and ATmega328P are deferred and have not been built or flashed. No upstream PR has been opened.

## Verification and reproduction

Run the commands in the component [README](../README.md). The archived H743 capture can be revalidated with:

```sh
python3 benchmarks/scripts/ingest_h743.py benchmarks/results/raw-logs/stm32h743 \
  --firmware benchmarks/results/raw-logs/stm32h743/firmware
```

The DFU log records successful erase/download followed by an error while requesting departure from DFU (exit 74). USB CDC subsequently enumerated and returned the exact expected Flash hash and complete result payload; those observations establish successful execution. Existing firmware was overwritten with explicit authorization and no backup was retained.

The shared benchmark tests, strict Clippy/doc checks and H743 preflight pass. The repository-wide test/release/format/API gates pass; strict repository-wide Clippy and documentation gates fail on existing upstream documentation issues (including missing safety sections and missing public documentation). Those failures are not reported as successful CI.
