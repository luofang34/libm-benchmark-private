//! Reproducible double-precision pow measurement kernels.
mod abi;
mod inputs;
mod kernel;
pub use inputs::{DOMAIN_NAMES, inputs};
pub use kernel::{IMPLEMENTATIONS, Measurement, measure, value};
