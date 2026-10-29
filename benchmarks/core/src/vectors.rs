/// Exact binary64 input pair; transport never passes through decimal formatting.
#[derive(Clone, Copy)]
pub struct Case {
    /// Bit pattern of the base.
    pub x: u64,
    /// Bit pattern of the exponent.
    pub y: u64,
}

/// One independently reported input distribution.
#[derive(Clone, Copy)]
pub struct Domain {
    /// Stable dataset label.
    pub name: &'static str,
    /// Offset in the shared input table.
    pub start: usize,
    /// Number of exact input pairs.
    pub count: usize,
    /// Preserve exceptional bit patterns during the dependency benchmark.
    pub special: bool,
}

include!("vectors/data.rs");

/// Retrieve the immutable cases for a known distribution.
pub fn cases(domain: Domain) -> &'static [Case] {
    DATA.get(domain.start..domain.start.saturating_add(domain.count))
        .unwrap_or(&[])
}
