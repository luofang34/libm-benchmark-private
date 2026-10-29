// SAFETY: this module defines the numeric WASM host ABI; it exposes no pointers.
#![allow(unsafe_code)]
#[cfg(target_arch = "wasm32")]
#[link(wasm_import_module = "env")]
unsafe extern "C" {
    safe fn clock_ms() -> f64;
    safe fn report(ns: f64, checksum: u64, calls: u32);
}
#[cfg(target_arch = "wasm32")]
pub(crate) fn now() -> f64 {
    clock_ms()
}

#[cfg(target_arch = "wasm32")]
#[unsafe(no_mangle)]
pub extern "C" fn run_bench(kind: u32, mode: u32, domain: u32, repeats: u32) {
    let r = crate::measure(kind, mode, domain, repeats);
    report(r.ns, r.checksum, r.calls as u32);
}
#[unsafe(no_mangle)]
pub extern "C" fn pow_value(kind: u32, x: f64, y: f64) -> f64 {
    crate::value(kind, x, y)
}

#[unsafe(no_mangle)]
pub extern "C" fn pow_bits(kind: u32, x: u64, y: u64) -> u64 {
    crate::value(kind, f64::from_bits(x), f64::from_bits(y)).to_bits()
}
