// Safe indexing keeps the experimental direct path inside this crate's unsafe prohibition.
macro_rules! i {
    ($array:expr, $index:expr) => {
        $array[$index]
    };
}

#[path = "../../../libm/src/math/pow.rs"]
// The shared source preserves libm's MSRV, which predates let chains.
#[allow(clippy::collapsible_if)]
mod implementation;

pub(crate) use implementation::pow;
