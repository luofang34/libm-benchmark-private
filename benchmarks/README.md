# Pow hardware benchmarks

The common `no_std` kernel compares upstream revision `6bc104a50f83cb205790c61c5d33508046f5fad3` with the local Arm pow candidate. `vectors/timing.bin` contains 448 exact binary64 pairs in seven separate distributions. Input generation, formatting, USB traffic and MPFR reference work occur outside timed intervals. There are five warmup rounds and at least 15 paired measurement rounds. Dependency measurements include feedback overhead and may traverse different inputs when results differ.

`boards/profiles.json` is the execution inventory. Capability classes are software FP32/FP64, hardware FP32 with software FP64, hardware FP64, and RP2350 DCP-assisted FP64. Planned capability is separate from emitted instructions and physical measurements. K230 CPU0/CPU1 and ATmega328P are deferred; their profiles must not cause compilation or flashing. K230's P0/P1 labels describe its two cores within that deferred phase.

`scripts/results.py` defines all required result columns and validation. CPU, explicit features, CPU defaults, ABI, runtime and compiler identify each run; a triple alone is insufficient. Speedups are medians of paired within-round ratios. Unknown sizes, cycles, stack usage and accuracy are blank, never zero placeholders. `ram_bytes` counts static `.data + .bss`; stack is separate. `measurement_status` and `accuracy_status` are independent.

From the repository root:

```sh
python3 benchmarks/scripts/generate_vectors.py --check
cargo test --manifest-path benchmarks/Cargo.toml --locked
python3 -m unittest discover -s benchmarks/scripts -p 'test_*.py'
python3 benchmarks/scripts/codegen.py --output benchmarks/results/codegen
python3 benchmarks/scripts/run_host.py
```

Host validation needs a C compiler and MPFR/GMP development libraries (Homebrew on macOS, `libmpfr-dev libgmp-dev` on Ubuntu). The manually dispatched `pow-hardware-hosts.yml` workflow tests Ubuntu x86-64 and AArch64 with the same kernel. Archived WASM experiments remain under `experiments/pow`; their datasets and timings are separate.

Accepted captures under `results/raw-logs/<device>/` retain their source metadata and per-round measurements. `python3 scripts/assemble_results.py` from this component directory regenerates the aggregate hardware, hosted and accuracy CSV files without combining different machines. `run_host.py` and `size_h743.py` accept `--source-revision` when a workspace tool uses a synthetic checkout commit; select the published revision containing the measured source.

## H743 USB2 firmware

`python3 benchmarks/scripts/build_h743.py` builds both algorithms in one image, runs Clippy, checks reset/stack bounds and actual pow calls, rejects unintended math libcalls, and records the flashable image hash. It needs the Rust `thumbv7em-none-eabihf` target and LLVM binary tools. The target is a 2 MiB STM32H743 using USB2 FS on PA11/PA12, internally clocked at nominal 200 MHz. It uses 512 KiB AXI SRAM, enables I-cache, preserves the bootloader's D-cache state, and disables interrupts during timing. Use the reported CCR for the actual cache configuration. DWT's 32-bit counter uses wrapping subtraction; batches are bounded well below a full wrap. Nanoseconds are derived from the configured clock, with internal oscillator uncertainty; cycles are the primary MCU metric.

The USB routing is confirmed by ST AN2606's H743 DFU interface. The HSI48 synchronization mux follows ST's revision-dependent USB2 selection. Physical PCB model remains unreported. No external oscillator, debugger wiring or GPIO LED assignment is assumed. Firmware reports silicon ID, UID, Flash size, FPSCR, FPU feature registers, cache state, dataset hash, and a SHA-256 of its own Flash load image.

`python3 benchmarks/scripts/collect.py --output benchmarks/results/runs/capture` discovers USB CDC ports and retrieves retained results. `POWBENCH/1 INFO` returns identity/state JSON; `POWBENCH/1 RESULTS` returns `BYTES N\n` followed by the exact payload. The collector verifies SHA-256 before persisting. The payload contains `TIMING\n` and `ACCURACY\n` CSV sections. Run `python3 benchmarks/scripts/ingest_h743.py benchmarks/results/runs/capture/capture-0` to verify the firmware hash, dataset, FPU mode and MPFR results before producing `hardware.csv`. It can fetch results again without reflashing.

`python3 benchmarks/scripts/size_h743.py` links separate single-algorithm fixtures with identical settings and input data. It verifies that each image contains only its selected pow implementation and records section sizes and replacement deltas. These fixtures have no transport or clock initialization and must not be flashed as measurement firmware. Stack usage remains unknown; static RAM is not peak RAM.

Device firmware images are not interchangeable with code-generation `.o` files. Each board needs a verified clock, memory layout, transport, image and flashing procedure before use. DCP requires its own runtime integration and precision result; an M33 build alone does not demonstrate DCP acceleration.

## F411 USB FS firmware

`python3 benchmarks/scripts/build_f411.py` audits the Cortex-M4 image for the connected 512 KiB F411 DFU device. It verifies hardware FP32 instructions, software FP64 helper calls, both pow calls and reset/stack bounds. The image uses 128 KiB SRAM and an 80 KiB stack-resident retained-result buffer. No H743 artifact may be flashed to this board.

The reset handler initializes SP and VTOR, disables inherited interrupts and stops SysTick before initializing RAM. If a successful DFU download does not produce USB CDC, release BOOT0 and power-cycle the board to boot from Flash; a DFU departure alone is not proof of application execution.

At startup TIM11 measures HSE/31 against HSI with an eight-edge capture prescaler and 256 intervals. Following the integer-MHz oscillator requirement of the F411 ROM DFU interface, the firmware rounds the estimate and rejects deviations above 1/66 of the nominal frequency. It reports both values. This identifies the crystal for PLL configuration, not precision oscillator calibration. A 48 MHz core/USB clock is selected to work within every F411 regulator voltage scale. Code and constants remain in internal Flash; the reported Flash ACR describes prefetch/cache settings. DWT timing, datasets and pow kernels match the H743 experiment.

Collect with `scripts/collect.py`, then run `python3 benchmarks/scripts/ingest_f411.py <capture>` to validate image identity, dataset completeness, FP32/software-FP64 mode, clocks and MPFR accuracy. `python3 benchmarks/scripts/size_f411.py` builds the two offline single-algorithm size fixtures. Factory signatures and clock registers can be unavailable through ROM DFU; the running firmware reports these directly. Reference: [STM32F411 RM0383, internal clock measurement](https://www.st.com/resource/en/reference_manual/DM00119316.pdf).

References: [ST bootloader resources](https://www.st.com/resource/en/application_note/cd00167594-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf), [ST H743](https://www.st.com/en/microcontrollers-microprocessors/stm32h743ig.html), [ST CRS implementation](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/master/Src/stm32h7xx_hal_rcc_ex.c), [RP2350 DCP runtime](https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2_common/pico_double/include/pico/double.h), [K230 cores](https://www.kendryte.com/k230/en/v2.0/K230_brief_datasheet.html).
