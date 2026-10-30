//! Probe the locally built compiler-builtins double-precision pow symbol.
#![no_std]
extern crate compiler_builtins;
extern crate panic_handler;

/// Return the result bits through the local double-precision C pow entry point.
// SAFETY: The unique export uses the WASM integer ABI to preserve all input bits.
#[unsafe(no_mangle)]
pub extern "C" fn pow_bits(x: u64, y: u64) -> u64 {
    compiler_builtins::math::partial_availability::pow(f64::from_bits(x), f64::from_bits(y))
        .to_bits()
}
