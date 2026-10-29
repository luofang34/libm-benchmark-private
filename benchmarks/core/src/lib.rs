//! Allocation-free pow kernels and fixed input vectors shared by host and MCU tests.
#![no_std]

#[cfg(feature = "direct-candidate")]
mod arm;
mod kernel;
mod vectors;

pub use kernel::{Implementation, Mode, Outcome, arithmetic_f32, arithmetic_f64, run, value};
pub use vectors::{Case, DOMAINS, Domain, cases};
