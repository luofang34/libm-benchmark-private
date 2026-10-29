//! Hosted paired timing and bit-exact output collection for the common pow kernel.
mod accuracy;

use std::io::{self, Write};
use std::time::Instant;

use pow_bench_core::{DOMAINS, Implementation, Mode, cases, run, value};

fn main() -> io::Result<()> {
    let mut out = io::BufWriter::new(io::stdout().lock());
    let mut args = std::env::args().skip(1);
    match args.next().as_deref() {
        Some("accuracy") => accuracy_blocking(&mut out)?,
        Some("accuracy-file") => {
            let path = args.next().ok_or_else(|| {
                io::Error::new(io::ErrorKind::InvalidInput, "accuracy-file requires a path")
            })?;
            accuracy::file_blocking(&mut out, &path)?;
        }
        _ => benchmark_blocking(&mut out)?,
    }
    out.flush()
}

fn benchmark_blocking(out: &mut impl Write) -> io::Result<()> {
    writeln!(
        out,
        "implementation,test_distribution,mode,round,ticks,timer_hz,calls,checksum"
    )?;
    for domain in DOMAINS {
        let data = cases(domain);
        for mode in [Mode::Throughput, Mode::Dependency] {
            let repeats = calibrate(data, mode, domain.special);
            for round in 0..20u32 {
                for offset in 0..2u32 {
                    let implementation = if (round + offset) % 2 == 0 {
                        Implementation::Baseline
                    } else {
                        Implementation::Candidate
                    };
                    let start = Instant::now();
                    let result = run(implementation, mode, data, repeats, domain.special);
                    let ticks = start.elapsed().as_nanos();
                    if round >= 5 {
                        writeln!(
                            out,
                            "{implementation:?},{},{mode:?},{},{ticks},1000000000,{},{:016x}",
                            domain.name,
                            round - 5,
                            result.calls,
                            result.checksum
                        )?;
                    }
                }
            }
        }
    }
    Ok(())
}

fn calibrate(data: &[pow_bench_core::Case], mode: Mode, special: bool) -> u32 {
    let mut repeats = 1u32;
    while repeats < 1 << 20 {
        let start = Instant::now();
        run(Implementation::Candidate, mode, data, repeats, special);
        if start.elapsed().as_millis() >= 5 {
            break;
        }
        repeats *= 2;
    }
    repeats
}

fn accuracy_blocking(out: &mut impl Write) -> io::Result<()> {
    writeln!(
        out,
        "test_distribution,index,x_bits,y_bits,baseline_bits,candidate_bits"
    )?;
    for domain in DOMAINS {
        for (i, pair) in cases(domain).iter().enumerate() {
            let x = f64::from_bits(pair.x);
            let y = f64::from_bits(pair.y);
            let old = value(Implementation::Baseline, x, y).to_bits();
            let new = value(Implementation::Candidate, x, y).to_bits();
            writeln!(
                out,
                "{},{i},{:016x},{:016x},{old:016x},{new:016x}",
                domain.name, pair.x, pair.y
            )?;
        }
    }
    Ok(())
}
