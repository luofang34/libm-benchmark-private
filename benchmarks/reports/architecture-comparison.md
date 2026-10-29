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

## RP2350: three distinct runtime populations

One RP2350 A2 QFN60 board, chip/USB ID `e4552bccfbae6dad`, completed three separate boots. ROM inspection reported 4 MiB Flash, ROM revision `0x312e22fa`, and Arm/RISC-V availability; the PCB model remains unreported. Each boot produced 420 timing rows and 448 exact accuracy pairs. Flash downloads were verified by picotool and the firmware's self-hash. Source is `486947580a6c980cc1ae8c091e9a79f4d823b281`, with Rust 1.99.0/LLVM 23.1.1, release optimization 3, fat LTO and one codegen unit.

| Population | Target / CPU / ABI | Runtime evidence | Flash SHA-256 |
|---|---|---|---|
| Arm software FP64 | `thumbv8m.main-none-eabihf` / `cortex-m33` / AAPCS VFP | FP32 instructions, FP64 helpers; CPACR `0xf0c003`, CP4 denied | `78ebd93d37c671837416e91074d6db0c1b719729c83fed9d24c1c5805c462eff` |
| Hazard3 software FP32/64 | `riscv32imac-unknown-none-elf` / `generic-rv32` / ILP32 | FP32/64 integer helpers; MISA `0x40901105`, F/D absent | `6131f511fa4f2e45ccb9eb365cb40d535d51b540e36465e7d833f53d9b872b80` |
| Arm DCP-assisted FP64 | Same M33 target / CPU / ABI, `dcp` feature | DCP instructions and add/multiply calls; CPACR `0xf0c303`, CP4 enabled | `e818da1aa3a461bed962e15a5ba0e5dd3d8578b4caa8b93a0f5732ca791e5129` |

The DCP integration is rp235x-hal 0.4.0, revision `fa430d279b8f185769fe2e5e9aca0e57290acd1f`. It replaces binary64 addition/multiplication only; other operations retain compiler helpers. This is not full hardware FP64 or a test of every Pico SDK double routine. Both Arm populations report MVFR0 `0x10110021` and FPSCR `0x10`; no FPU flush-to-zero/default-NaN mode is enabled. The DCP has separate arithmetic semantics.

The nominal core clock is 150 MHz. Checks against 100 USB SOF intervals observed 149,999,780 Hz (Arm software), 150,000,940 Hz (Hazard3), and 150,000,470 Hz (DCP). This validates the clock conversion to within the 0.5% acceptance threshold, not a precision calibration. Each core uses its cycle counter, disabled interrupts, XIP Flash code/tables and striped SRAM stack. XIP CTRL is `0x83` in all three boots. Five warmups precede 15 alternating paired rounds. These are single-boot populations, without repeated power-cycle statistics.

| Ordinary-positive throughput | Baseline cycles/op | Candidate cycles/op | Paired speedup (p10–p90) | Dependency speedup | Accuracy acceptance |
|---|---:|---:|---:|---:|---|
| M33 software FP64 | 12,460.66 | 9,272.02 | 1.349× (1.330–1.361) | 1.357× | PASS |
| Hazard3 software FP32/64 | 11,923.17 | 8,859.28 | 1.348× (1.315–1.377) | 1.366× | PASS |
| M33 DCP add/multiply | 6,098.97 | 3,202.59 | 1.908× (1.841–1.917) | 1.894× | **FAIL; diagnostic timing only** |

Paired speedup is the median of within-round ratios, not the ratio of the two medians. Per-implementation p10–p90, nanoseconds, checksums and exact rounds are in the separate [Arm](../results/raw-logs/rp2350-arm/hardware.csv), [Hazard3](../results/raw-logs/rp2350-riscv/hardware.csv) and [DCP](../results/raw-logs/rp2350-dcp/hardware.csv) captures.

| Distribution | Arm throughput / dependency | Hazard3 throughput / dependency | DCP throughput / dependency (accuracy FAIL) |
|---|---:|---:|---:|
| Near one, large exponent | 1.013× / 1.014× | 1.082× / 1.079× | 1.340× / 1.333× |
| Small/large magnitudes | 1.323× / 1.322× | 1.352× / 1.346× | 1.888× / 1.890× |
| Negative, integer exponent | 1.258× / 1.258× | 1.333× / 1.265× | 1.699× / 1.697× |
| Subnormal | 1.143× / 1.145× | 1.024× / 1.109× | 1.398× / 1.400× |
| Overflow/underflow edge | 1.056× / 1.055× | 0.871× / 0.970× | 1.352× / 1.345× |
| Special values | 0.658× / 0.595× | 0.637× / 0.601× | 0.605× / 0.529× |

## RP2350 accuracy and DCP limitation

MPFR 4.2.2 at 256-bit precision gives the same passing maxima for M33 software and Hazard3: candidate `0.4999999999955404` ULP and baseline `0.6710095080248282` ULP. No NaN/infinity classification or signed-zero mismatch occurred. These 448-pair observations do not establish a whole-domain error bound.

**The DCP runtime fails acceptance for both algorithms.** Each has 45 of 64 subnormal-domain cases above 2 ULP. Observed maximum errors are `8,925,239,461,535,591` ULP (candidate) and `8,925,239,526,489,353` ULP (baseline). For input bits `x=0004893275cede07`, `y=3fdf91a483715e39`, the MPFR-rounded result is `205fb5754d026bca`; DCP candidate returns `1ecabd18c7929d9b`, baseline `1ec2fedd8283523a`. Candidate also returns +0 for `pow(2^-1074, 1)` instead of `2^-1074`. There are no NaN/infinity classification or signed-zero mismatches, which does not excuse these finite-result errors. Complete bins and worst cases remain in [accuracy.csv](../results/raw-logs/rp2350-dcp/accuracy.csv).

The errors occur with both algorithms only in the DCP configuration, implicating that arithmetic integration rather than establishing a pow-port-only defect. Raspberry Pi documents that its optimized [RP2350 double runtime](https://www.raspberrypi.com/documentation/pico-sdk/runtime.html#pico_double) does not implement every fully compliant floating-point behavior. This experiment does not isolate hardware versus assembly handling or validate a corrected DCP runtime. No DCP correction is included in the pow patch.

The ingester rejects this capture by default. `--record-accuracy-failure` retains its verified timing with every row marked `accuracy_status=FAIL`; it never bypasses firmware, corpus or capability verification. Consequently, DCP's faster finite-normal timings cannot be used as evidence of an IEEE-compatible replacement.

## RP2350 replacement size

Six offline single-algorithm fixtures keep the same runtime settings, corpus and compute loop within each population. They contain only the selected pow implementation, and use no USB telemetry.

| Population | Baseline Flash bytes | Candidate Flash bytes | Flash delta | Text delta | Read-only data delta |
|---|---:|---:|---:|---:|---:|
| M33 software FP64 | 15,872 | 19,520 | **+3,648** | −1,196 | +4,816 |
| Hazard3 software FP32/64 | 19,776 | 23,360 | **+3,584** | −1,256 | +4,816 |
| M33 DCP add/multiply | 15,264 | 18,880 | **+3,616** | −1,196 | +4,816 |

Flash sizes include image alignment. Each size fixture has zero static `.data + .bss`; peak stack is unmeasured. The dual-algorithm telemetry images occupy 64,128 / 74,144 / 63,520 Flash bytes and 4 / 32 / 4 static RAM bytes respectively, excluding the 128 KiB stack-resident payload and other frames. These figures establish isolated MCU replacement costs, not compressed large-WASM marginal costs or exp/log table sharing. Full linked artifacts and manifests accompany each capture.

## RP2040: Cortex-M0+ with software FP32/FP64

The RP2040 B2 completed 420 batches and 448 accuracy pairs using source `319d5046d42c7de1c5641d622a9e23b77918ed07`. BOOTSEL serial is `E0C9125B0D9B`, Flash UID `e66430a64b826d39`, JEDEC `0xef4015`, and picotool reports 2048 KiB Flash. The PCB model is unreported. Firmware self-hash matches `102f316b03c6ff193eb242f66a76b0c4f59bce451074cf88b1ba14d305497141`.

Build settings are `thumbv6m-none-eabi`, `cortex-m0plus`, AAPCS soft-float, Rust 1.99.0 and LLVM 23.1.1. HAL `disable-intrinsics` keeps FP32/64 arithmetic in Rust compiler helpers; linked calls are checked, and no hardware FP, automatic ROM floating-point substitutions or FMA libcalls are present. This population measures the compiler software runtime, not the optimized Pico ROM routines.

The nominal core clock is 125 MHz; a 50-frame USB SOF cross-check observes 124,990,780 Hz. SysTick uses the core clock with IRQ disabled (`CSR=0x10005`), and every timed batch is checked against the independent microsecond timer. The longest batch, including warmups, is 23,147 µs; every accepted interval is below the 100 ms guard and the 134.2 ms counter-wrap period. Core 1 stays parked in ROM, interrupts are disabled, and USB work remains outside timing.

Code/tables use cached XIP Flash (`XIP CTRL=3`) with one-bit 03h reads at 31.25 MHz (`BAUDR=4`, `SPI_CTRLR0` readback `0x218`). The boot block writes command configuration `0x03000218`; the command high byte is not present in the observed register readback. An audited SRAM routine sets divider 4 before raising PLL_SYS. The retained [divider-2 capture](../results/raw-logs/rp2040/rejected-spi-div2/rejection.json) is excluded: 62.5 MHz exceeds the 50 MHz 03h limit in the [Winbond W25Q16JV datasheet](https://www.mouser.com/datasheet/2/949/w25q16jv_spi_revg_03222018_plus-1489727.pdf). These timings do not represent optimized QSPI execution.

| Distribution | Baseline throughput cycles/op | Candidate throughput cycles/op | Paired throughput speedup | Paired dependency speedup |
|---|---:|---:|---:|---:|
| Ordinary positive | 44,470.00 | 28,851.67 | 1.547× | 1.569× |
| Near one, large exponent | 28,095.64 | 24,093.45 | 1.169× | 1.167× |
| Small/large magnitudes | 42,505.47 | 28,903.03 | 1.479× | 1.468× |
| Negative, integer exponent | 38,397.66 | 27,351.91 | 1.410× | 1.405× |
| Subnormal | 40,049.03 | 31,783.75 | 1.266× | 1.269× |
| Overflow/underflow edge | 34,580.08 | 27,694.69 | 1.252× | 1.245× |
| Special values | 4,512.06 | 6,466.38 | 0.708× | 0.669× |

Ordinary-positive baseline/candidate medians are 355.760 / 230.813 µs per operation. Their p10–p90 ranges are 348.708–358.987 / 227.114–237.483 µs; paired speedup p10–p90 is 1.470–1.575×. Both throughput checksums are `fc1bd58af9638b1a`. As with other boards, five warmups and 15 paired rounds describe one boot, not power-cycle variability; dependency measurements include feedback overhead. Every round is retained in [timing.csv](../results/raw-logs/rp2040/timing.csv).

MPFR 4.2.2 at 256-bit precision observes candidate maximum `0.4999999999955404` ULP and baseline `0.67100950802482817` ULP. No classification or signed-zero mismatches occur. Subnormal and range-edge inputs pass. This targeted 448-pair corpus does not prove a whole-domain error bound.

Separate single-algorithm fixtures use 16,080 / 19,480 Flash bytes: **+3,400 bytes** for the candidate. Text changes from 8,160 to 6,740 bytes (−1,420); read-only data from 7,472 to 12,288 (+4,816); both have zero static RAM. These offline fixtures establish isolated replacement costs without measuring stack use or exp/log table sharing. The dual-algorithm measurement image occupies 66,920 Flash bytes and 168 static RAM bytes, excluding the 128 KiB stack-resident payload and other frames. Exact [size artifacts](../results/raw-logs/rp2040/size/manifest.json) preserve the distinction.

## Interpretation and remaining hardware

The approximately 3× WASM improvement does not generalize to these MCUs. Ordinary-positive throughput gains are 1.173× on H743 and 1.358× on F411. H743 near-one inputs regress about 10%; the special-value mixture takes about 43% longer on H743 and 55% longer on F411. This evidence does not yet justify a universal replacement for all embedded targets. RP2350 software FP64 gains are also about 1.35× on ordinary-positive input, with input-dependent regressions; its tested DCP runtime fails accuracy. RP2040 compiler-software FP64 gains 1.547× on ordinary-positive input, but its special-value mixture regresses to 0.708×. The four capability classes now have hardware observations, but the DCP class has no passing IEEE result.

Nine target profiles pass compilation and instruction/helper inspection in [codegen.json](../results/codegen/codegen.json). Those unlinked objects are not board measurements. Unconnected boards remain explicitly blocked in [profiles.json](../boards/profiles.json). K230 CPU0/CPU1 and ATmega328P are deferred and have not been built or flashed. No upstream PR has been opened.

## ESP32-C6: ROM software FP32/FP64

The ESP32-C6 v0.1, MAC `f0:f5:bd:0c:22:88`, completed 420 timed batches and 448 accuracy pairs through USB Serial/JTAG CDC (`303a:1001`). ROM identification reports a 40 MHz crystal and 8 MiB Flash; the PCB model remains unreported. Source is `dae5e159d1d17f208e9832bc0863b86d911fa5d3`; the running application's self-hash matches `fe65c2c9d89a8d41f3818f0598a7cce3e96dbfebc710574d8f594a8f39d3c2b5`. The successful flash log and complete boot/capture evidence are in [raw-logs/esp32c6](../results/raw-logs/esp32c6/).

The HP core uses `riscv32imac-unknown-none-elf`, `generic-rv32`, ILP32, Rust 1.99.0/LLVM 23.1.1, optimization 3, fat LTO and one codegen unit. MISA reports no F/D extensions. This population uses **Espressif ROM software floating point**, not Rust compiler arithmetic helpers. Decoded AUIPC/JALR targets confirm binary64 add/multiply/divide calls to `0x400009f4`, `0x40000a64`, and `0x400008d0`; the FP32 probe also reaches the corresponding ROM helpers. These addresses follow the pinned [esp-rom-sys runtime](https://github.com/esp-rs/esp-hal/blob/160b10794227eb84805b8676fe188c1110801e9d/esp-rom-sys/ld/esp32c6/rom/esp32c6.rom.rvfp.ld). No hardware FP or unintended pow/exp/log/FMA libcall is found.

The nominal core clock is 160 MHz; the SYSTIMER check observes 159,962,003 Hz. MPCER=1 selects cycles, MPCMR=1 enables wrapping, and MSTATUS.MIE=0 disables interrupts. Each batch is cross-checked against SYSTIMER; the longest batch including warmups is 3,999 microseconds. No radio, RTOS or LP-core workload starts. These are clock-ratio checks, not absolute crystal calibration. Five warmups precede 15 alternating paired rounds in one accepted boot; the narrow intervals do not establish across-boot or across-board variability.

**Actual cached Flash is DIO at 80 MHz**, although the image header requests 40 MHz. The [HAL clock initialization](https://github.com/esp-rs/esp-hal/blob/5ba50dd2d21136370050dd2f7a767761e01cfeef/esp-hal/src/clock/clocks_ll/esp32c6.rs) selects PLL 480/6 for MSPI. Captured MSPI_CONF=`0x500`, SPI_CLOCK=`0x80000000`, SYSCLK=`0x28010000`, and CACHE_CTRL=0 confirm that source, divider 1 and enabled cache access. The ingester enforces these settings so a header field cannot substitute for measured runtime configuration.

| Ordinary-positive mode | Baseline cycles/op | Candidate cycles/op | Candidate ns/op (p10–p90) | Paired speedup (p10–p90) |
|---|---:|---:|---:|---:|
| Throughput | 9,847.05 | 6,998.91 | 43,743.16 (43,743.16–43,743.46) | 1.406941× (1.406925–1.406941) |
| Dependency | 9,853.63 | 7,000.89 | 43,755.57 (43,755.57–43,755.86) | 1.407482× (1.407466–1.407482) |

| Distribution | Throughput speedup | Dependency speedup |
|---|---:|---:|
| Near one, large exponent | 1.136× | 1.136× |
| Small/large magnitudes | 1.378× | 1.378× |
| Negative, integer exponent | 1.308× | 1.305× |
| Subnormal | 1.175× | 1.175× |
| Overflow/underflow edge | 1.073× | 1.073× |
| Special values | **0.720×** | **0.784×** |

All checksums, per-round timings and both implementations' intervals are retained in [hardware.csv](../results/raw-logs/esp32c6/hardware.csv) and [timing.csv](../results/raw-logs/esp32c6/timing.csv). MPFR at 256 bits accepts every pair: candidate observed maximum `0.4999999999955404` ULP, baseline `0.6710095080248282` ULP, with zero classification or signed-zero mismatches. This finite corpus does not prove a global error bound.

Separate offline compute fixtures occupy 16,960 bytes (baseline) and 20,480 bytes (candidate), a **3,520-byte Flash increase**. Text changes by −1,282 bytes, read-only data by +4,864 bytes, and static RAM by −48 bytes (2,668 → 2,620, including IRAM code). Image padding/checksum/hash are included; the common bootloader and partition table are excluded. Peak stack is unmeasured. The dual-algorithm telemetry app is 60,816 bytes with 4,324 bytes of static RAM including IRAM, excluding its 128 KiB retained payload and other stack frames. Size fixtures use source `b33d67631e55fd0790ab3e2d198d17993d547ecd`; their math/size entry points are unchanged by the telemetry register fields. These are MCU replacement costs, not compressed application deltas.

## Hosted hardware comparison

The compile-time selected public `libm::pow` ran on four hosted target groups, each with separate default-CPU and native-CPU builds. Math/kernel source is `f39774d821b2bbc19c98dca827678fdce636d075`; Rust is 1.99.0 and LLVM 23.1.1. The [private workflow](https://github.com/luofang34/libm-benchmark-private/actions/runs/40939173049) passed on both Linux architectures and Windows. Its three downloaded ZIPs match GitHub's [recorded SHA-256 digests](../results/raw-logs/target-scope/workflow-artifacts.json). Local Mac measurements use the same source and runner.

| Observed host | Build / LLVM CPU | Positive baseline ns/op | Positive candidate ns/op | Paired throughput speedup (p10–p90) | Dependency speedup |
|---|---|---:|---:|---:|---:|
| Apple M3 Max; macOS AArch64 | default / `apple-m1` | 31.826 | 9.673 | 3.293× (3.248–3.338) | 2.468× |
| Apple M3 Max; macOS AArch64 | native / `apple-m3` | 31.669 | 9.620 | 3.292× (3.232–3.345) | 2.442× |
| Arm VM (implementer 0x41, part 0xd49); GNU/Linux AArch64 | default / `generic` | 46.997 | 19.176 | 2.451× (2.448–2.452) | 2.464× |
| Arm VM (implementer 0x41, part 0xd49); GNU/Linux AArch64 | native / `neoverse-n2` | 46.099 | 20.449 | 2.253× (2.249–2.257) | 2.221× |
| AMD EPYC 9V45 VM; GNU/Linux x86-64 | default / `x86-64` | 27.035 | 10.920 | 2.481× (2.446–2.532) | 2.261× |
| AMD EPYC 9V45 VM; GNU/Linux x86-64 | native / `znver5` | 25.807 | 10.357 | 2.469× (2.449–2.506) | 2.263× |
| AMD EPYC 7763 VM; Windows Server 2025 MSVC x86-64 | default / `x86-64` | 49.075 | 17.933 | 2.735× (2.638–2.827) | 2.303× |
| AMD EPYC 7763 VM; Windows Server 2025 MSVC x86-64 | native / `znver3` | 47.870 | 16.586 | 2.923× (2.484–3.286) | 2.280× |

Five warmups precede 15 alternating paired rounds in every domain/mode. These are OS-scheduled, unpinned executions; cycle counts and unmeasured section/stack sizes remain blank. The Arm VM does not expose a SoC product name. CPU implementer/part, raw OS identity, ABI, compiler CPU and effective features are retained in each `environment.json`, without treating every triple or GitHub VM as identical. Windows runs an MSVC-built Rust executable; MSYS2 GCC builds only the external MPFR reference checker. Earlier native-only captures remain separately identified in [hosted.csv](../results/hosted.csv).

All 14 domain/mode combinations improve in these eight hosted builds, but the gain varies: ordinary-positive throughput is 2.253–3.293×; near-one throughput is 1.548–2.118×; range-edge dependency is only 1.053× on the Mac native build. The special mixture improves on these hosts, unlike the MCU populations above. Full medians, p10–p90, checksums and source identities remain in the CSV and `raw-logs/*-pow-{default,native}/`. One run per host/configuration does not establish performance across all processors or future runner populations.

Every executable independently passes both the 448-pair timing corpus and the archived **151,083-pair** random/boundary/adversarial corpus against 256-bit MPFR. In the larger corpus, baseline/candidate maximum observed errors are **0.7858855121846906 / 0.5055620758593419 ULP**. Candidate bins are 8,734 exact, 122,196 in (0,0.5], and 107 in (0.5,1], with zero classification/signed-zero mismatches. [large-accuracy.csv](../results/raw-logs/target-scope/large-accuracy.csv) keeps target and CPU identity beside every distribution. These are repeated executions of the same inputs, not eight independent random corpora or a global error proof. NaN payload identity across platforms is not required.

The first Windows job stopped while checking generated input files, before timing. Generated text is now pinned to LF and quiet-NaN inputs to an explicit bit pattern; the successful run verifies the same corpus hash as Linux/macOS. The [failed log](../results/raw-logs/target-scope/windows-first-attempt.log) is retained and never counted as a measurement.

## Verification and reproduction

Run the commands in the component [README](../README.md). The archived H743 capture can be revalidated with:

```sh
python3 benchmarks/scripts/ingest_h743.py benchmarks/results/raw-logs/stm32h743 \
  --firmware benchmarks/results/raw-logs/stm32h743/firmware
```

The DFU log records successful erase/download followed by an error while requesting departure from DFU (exit 74). USB CDC subsequently enumerated and returned the exact expected Flash hash and complete result payload; those observations establish successful execution. Existing firmware was overwritten with explicit authorization and no backup was retained.

For F411, both DFU downloads exited successfully, but departure did not establish CDC. A BOOT0-released power cycle produced CDC and the complete matching capture. The successful image explicitly initializes startup state; the experiment does not isolate which bootloader state caused the departure failure. Revalidate without hardware using `python3 benchmarks/scripts/ingest_f411.py benchmarks/results/raw-logs/stm32f411 --firmware benchmarks/results/raw-logs/stm32f411/firmware`. No original Flash backup was retained.

The shared benchmark's four Rust tests, 36 Python tests, strict Clippy/doc checks and H743/F411/RP2350/RP2040/ESP32-C6 build preflights pass. RP2350 regression tests reprocess the real captures and require the DCP accuracy failure to remain visible; passing test execution does not mean that DCP arithmetic passed accuracy. The repository-wide tests (2,198 passed), release, format and API gates pass using nightly `41089d07a`; the API script also requires `RUSTUP_TOOLCHAIN=nightly`. Stable cannot compile the root compiler-builtins workspace's nightly features. Strict repository-wide Clippy and documentation gates fail on existing upstream documentation issues (including 105 compiler-builtins Clippy errors for missing safety sections and other documentation issues). Those failures are not reported as successful CI.

Revalidate RP2350 using `python3 benchmarks/scripts/ingest_rp2350.py benchmarks/results/raw-logs/rp2350-<mode> --firmware benchmarks/results/raw-logs/rp2350-<mode>/firmware`. Arm and Hazard3 pass normally; DCP requires the explicit failed-evidence option described above. All three flashes were verified, booted directly to USB CDC, and returned matching hashes; no original Flash backup was retained.

Revalidate RP2040 using `python3 benchmarks/scripts/ingest_rp2040.py benchmarks/results/raw-logs/rp2040 --firmware benchmarks/results/raw-logs/rp2040/firmware`. The accepted flash verified and booted directly to CDC. Regression checks cover the real capture, rejected Flash divider, incorrect SysTick/USB clock, inconsistent batch interval and firmware substitution. Archived gate logs preserve successful benchmark/firmware checks and the repository-wide documentation failures described above.

Revalidate C6 with `python3 benchmarks/scripts/ingest_c6.py benchmarks/results/raw-logs/esp32c6 --firmware benchmarks/results/raw-logs/esp32c6/firmware`. Regression checks reprocess the real capture and image; they reject counter saturation, wrong clock/memory settings, inconsistent intervals, firmware substitution, image corruption/truncation, and mismatched ROM symbols. The collector's PTY test covers boot output immediately adjacent to its metadata frame. C6 firmware checks use its cross target; host test harnesses cannot run on this bare-metal binary. Shared-kernel host tests and the complete physical execution provide the runtime validation. No original Flash backup was retained.

## Compile-time scope and upstream review

The [standalone patch](../../experiments/pow/libm-pow-arm.patch) selects the non-FMA table algorithm for `wasm32-unknown-unknown`, AArch64 macOS, AArch64 GNU/Linux, x86-64 GNU/Linux, and x86-64 Windows MSVC. AArch64 additionally requires the `neon` target feature; x86-64 requires `sse2`. All other targets select the preserved fdlibm implementation. This is an explicit compile-time allowlist, with no runtime dispatch, public feature or API change. `powf(f32)` and every other math function stay outside the patch.

The seven-file math-only diff contains the algorithm, tables, regression tests, target selection and fallback; it excludes the private CI and benchmark infrastructure. Fallback production arithmetic is byte-identical to the upstream source apart from localizing its word-setting helper. Shared tests avoid duplicating the test body. [Patch verification](../results/raw-logs/target-scope/patch-verification.json) checks application to upstream `6bc104a50f83cb205790c61c5d33508046f5fad3`, reverse applicability, and byte equality of all seven resulting files.

Actual release objects from [11 targets](../results/raw-logs/target-scope/codegen/scope.json) contain both complete tables exactly once on the five selected targets and neither table on WASI, AArch64 bare metal, Cortex-M hard-float, RV32 bare metal, iOS and x86-64 macOS. The [reachable pow call graph](../results/raw-logs/target-scope/codegen/pow-callgraph.json) on all five selected targets has only `llvm.fabs.f64` outside its own definitions, with no math or FMA libcall. This is code-generation evidence, separate from hardware execution. MCU benchmark crates explicitly enable `direct-candidate`; their candidate cannot silently turn into the fallback. The C6 linked build passes the same ROM-helper audit with this direct path, without reflashing or replacing its archived physical measurement.

Rust **1.67.0** builds the unchanged production library source for AArch64 macOS, WASM and Cortex-M fallback in an isolated library-only manifest; development dependencies are omitted to avoid modern workspace resolution. [MSRV logs](../results/raw-logs/target-scope/gates/msrv.json) preserve that scope. Ten pow tests pass with `assert_no_panic`, and the upstream MPFR extensive harness passes **1,000,000** spaced pairs in `release-checked`. Existing repository-wide strict Clippy/doc failures remain disclosed above. These checks do not substitute for all upstream CI targets or rounding modes.

Rebuilt ordinary WASM `std::powf` also uses the selection: positive throughput improves **3.12×**, dependency kernel **2.53×**, and all 151,083 outputs agree with direct candidate results and MPFR acceptance. The representative application grows **3,551 gzip / 3,272 Brotli bytes** under the paired sysroot builds. [STD_INTEGRATION.md](../../experiments/pow/STD_INTEGRATION.md) records actual call paths, code sizes and limits. Hosted measurements establish direct Rust `libm::pow` gains; native `std::powf` generally calls a platform library and is not accelerated by this patch.

The maintainer's [review of log2f #1347](https://github.com/rust-lang/compiler-builtins/pull/1347#pullrequestreview-5482130704) requires compatible provenance and explains that ordinary libm does not guarantee cross-platform bit reproducibility. Their [follow-up](https://github.com/rust-lang/compiler-builtins/pull/1347#issuecomment-6167996403) asks for benchmark evidence; this is not approval of the present pow translation or its scope. The candidate derives from [ARM optimized-routines](https://github.com/ARM-software/optimized-routines/blob/2ee4b0d45680a9880412c1d186224b08652c35f6/math/pow.c), selecting its MIT license and retaining attribution/permission text. No glibc or Petir implementation is incorporated.

The evidence supports discussing a narrow f64-pow proposal for these measured target groups. Default-CPU support does not establish every hardware/feature combination, and the table cost plus maintenance of two algorithms are real tradeoffs. An upstream review should keep the source/rounding differences, worst observed ULP, domain-dependent timings and marginal bytes visible. WASI, musl, Windows GNU/ARM64, RISC-V Linux and bare metal remain fallback targets; K230 and ATmega stay deferred. No upstream PR has been opened.
