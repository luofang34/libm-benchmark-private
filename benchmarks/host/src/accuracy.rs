use std::fs::File;
use std::io::{self, BufReader, Read, Write};

use pow_bench_core::{Implementation, value};

pub(crate) fn file_blocking(out: &mut impl Write, path: &str) -> io::Result<()> {
    let file = File::open(path)?;
    let bytes = file.metadata()?.len();
    if bytes == 0 || bytes % 16 != 0 {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("{path}: expected complete binary64 input pairs"),
        ));
    }
    let mut input = BufReader::new(file);
    writeln!(
        out,
        "test_distribution,index,x_bits,y_bits,baseline_bits,candidate_bits"
    )?;
    for index in 0..bytes / 16 {
        let mut xb = [0u8; 8];
        let mut yb = [0u8; 8];
        input.read_exact(&mut xb)?;
        input.read_exact(&mut yb)?;
        let x = u64::from_le_bytes(xb);
        let y = u64::from_le_bytes(yb);
        let old = value(
            Implementation::Baseline,
            f64::from_bits(x),
            f64::from_bits(y),
        )
        .to_bits();
        let new = value(
            Implementation::Candidate,
            f64::from_bits(x),
            f64::from_bits(y),
        )
        .to_bits();
        writeln!(
            out,
            "random_bits,{index},{x:016x},{y:016x},{old:016x},{new:016x}"
        )?;
    }
    Ok(())
}
