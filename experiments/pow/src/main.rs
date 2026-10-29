use pow_experiment::{DOMAIN_NAMES, IMPLEMENTATIONS, measure};
use std::io::{self, Write};
fn main() -> io::Result<()> {
    let stdout = io::stdout();
    let mut out = io::BufWriter::new(stdout.lock());
    writeln!(
        out,
        "runtime,implementation,domain,mode,round,ns_per_op,checksum,calls"
    )?;
    for domain in 0..6u32 {
        for mode in 0..2u32 {
            for round in 0..20u32 {
                for offset in 0..5u32 {
                    let kind = (offset + round) % 5;
                    let r = measure(kind, mode, domain, 32);
                    if round >= 5 {
                        writeln!(
                            out,
                            "native,{},{},{},{},{:.6},{:016x},{}",
                            IMPLEMENTATIONS[kind as usize],
                            DOMAIN_NAMES[domain as usize],
                            if mode == 0 {
                                "throughput"
                            } else {
                                "dependency"
                            },
                            round - 5,
                            r.ns / r.calls as f64,
                            r.checksum,
                            r.calls
                        )?;
                    }
                }
            }
        }
    }
    out.flush()
}
