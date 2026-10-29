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

## H743 USB2 firmware

`python3 benchmarks/scripts/build_h743.py` builds both algorithms in one image, runs Clippy, checks reset/stack bounds and actual pow calls, rejects unintended math libcalls, and records the flashable image hash. It needs the Rust `thumbv7em-none-eabihf` target and LLVM binary tools. The target is a 2 MiB STM32H743 using USB2 FS on PA11/PA12, internally clocked at nominal 200 MHz. It uses 512 KiB AXI SRAM, I-cache on, D-cache off, and no enabled interrupts during timing. DWT's 32-bit counter uses wrapping subtraction; batches are bounded well below a full wrap. Nanoseconds are derived from the configured clock, with internal oscillator uncertainty; cycles are the primary MCU metric.

The USB routing is confirmed by ST AN2606's H743 DFU interface. The HSI48 synchronization mux follows ST's revision-dependent USB2 selection. Physical PCB model remains unreported. No external oscillator, debugger wiring or GPIO LED assignment is assumed. Firmware reports silicon ID, UID, Flash size, FPSCR, FPU feature registers, cache state, dataset hash, and a SHA-256 of its own Flash load image.

`python3 benchmarks/scripts/collect.py --output benchmarks/results/runs/capture` discovers USB CDC ports and retrieves retained results. `POWBENCH/1 INFO` returns identity/state JSON; `POWBENCH/1 RESULTS` returns `BYTES N\n` followed by the exact payload. The collector verifies SHA-256 before persisting. The payload contains `TIMING\n` and `ACCURACY\n` CSV sections. A capture is transport evidence, not an accuracy pass: run the MPFR checker separately and compare the reported firmware hash against `firmware/h743/manifest.json` before accepting hardware results. It can fetch results again without reflashing.

Device firmware images are not interchangeable with code-generation `.o` files. Each board needs a verified clock, memory layout, transport, image and flashing procedure before use. DCP requires its own runtime integration and precision result; an M33 build alone does not demonstrate DCP acceleration.

References: [ST bootloader resources](https://www.st.com/resource/en/application_note/cd00167594-stm32-microcontroller-system-memory-boot-mode-stmicroelectronics.pdf), [ST H743](https://www.st.com/en/microcontrollers-microprocessors/stm32h743ig.html), [ST CRS implementation](https://github.com/STMicroelectronics/stm32h7xx-hal-driver/blob/master/Src/stm32h7xx_hal_rcc_ex.c), [RP2350 DCP runtime](https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2_common/pico_double/include/pico/double.h), [K230 cores](https://www.kendryte.com/k230/en/v2.0/K230_brief_datasheet.html).
