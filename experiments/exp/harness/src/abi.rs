// SAFETY: the host ABI passes numbers by value and exposes no memory pointers.
#![allow(unsafe_code)]

#[cfg(target_arch = "wasm32")]
#[link(wasm_import_module = "env")]
unsafe extern "C" {
    safe fn clock_ms() -> f64;
    safe fn report(ns: f64, checksum: u64, calls: u64);
}

#[cfg(target_arch = "wasm32")]
pub(crate) fn now() -> f64 {
    clock_ms()
}

#[cfg(target_arch = "wasm32")]
#[unsafe(no_mangle)]
pub extern "C" fn run_bench(function: u32, kind: u32, mode: u32, domain: u32, repeats: u32) {
    let result = crate::kernel::measure(function, kind, mode, domain, repeats);
    report(result.ns, result.checksum, result.calls);
}

#[cfg(not(target_arch = "wasm32"))]
#[unsafe(no_mangle)]
pub extern "C" fn run_bench(
    function: u32,
    kind: u32,
    mode: u32,
    domain: u32,
    repeats: u32,
) -> crate::Measurement {
    crate::kernel::measure(function, kind, mode, domain, repeats)
}

#[unsafe(no_mangle)]
pub extern "C" fn unary_bits(function: u32, kind: u32, bits: u64) -> u64 {
    crate::kernel::value(function, kind, f64::from_bits(bits)).to_bits()
}
