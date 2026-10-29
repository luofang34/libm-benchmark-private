// SAFETY: numeric WASM exports have no pointers or shared state.
#![allow(unsafe_code)]
#[unsafe(no_mangle)]
pub extern "C" fn power(x: f64, y: f64) -> f64 {
    x.powf(y)
}

#[cfg(feature = "medium")]
#[unsafe(no_mangle)]
pub extern "C" fn math_kernel(x: f64, y: f64) -> f64 {
    let (s, c) = x.sin_cos();
    x.powf(y) + x.exp() + x.exp2() + x.ln() + x.log2() + s + c + x.atan2(y)
}

#[cfg(feature = "application")]
#[unsafe(no_mangle)]
pub extern "C" fn portfolio_report(rate: f64, periods: u32) -> u64 {
    crate::portfolio::report(rate, periods)
}
