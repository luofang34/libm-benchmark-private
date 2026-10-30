// SAFETY: each export takes and returns numbers by value, with no memory pointers.
#![allow(unsafe_code)]

#[cfg(feature = "exp")]
#[unsafe(no_mangle)]
pub extern "C" fn exponential(x: f64) -> f64 {
    libm::exp(x)
}

#[cfg(feature = "exp2")]
#[unsafe(no_mangle)]
pub extern "C" fn binary_exponential(x: f64) -> f64 {
    libm::exp2(x)
}

#[cfg(feature = "medium")]
#[unsafe(no_mangle)]
pub extern "C" fn power(x: f64, y: f64) -> f64 {
    libm::pow(x, y)
}

#[cfg(feature = "medium")]
#[unsafe(no_mangle)]
pub extern "C" fn math_kernel(x: f64, y: f64) -> f64 {
    let positive = libm::fabs(x) + 0.5;
    libm::pow(positive, y)
        + libm::exp(x)
        + libm::exp2(x)
        + libm::log(positive)
        + libm::log2(positive)
        + libm::sin(x)
        + libm::cos(x)
        + libm::atan2(x, y)
}

#[cfg(feature = "application")]
#[unsafe(no_mangle)]
pub extern "C" fn portfolio_report(rate: f64, periods: u32) -> u64 {
    crate::portfolio::report(rate, periods)
}
