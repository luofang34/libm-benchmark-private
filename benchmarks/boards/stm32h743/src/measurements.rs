use core::fmt::Write;

use cortex_m::peripheral::DWT;
use heapless::String;
use pow_bench_core::{DOMAINS, Implementation, Mode, cases, run, value};

pub type Payload = String<131072>;

pub fn measure(payload: &mut Payload, hz: u32, mut poll: impl FnMut()) -> core::fmt::Result {
    writeln!(
        payload,
        "TIMING\nimplementation,test_distribution,mode,round,ticks,timer_hz,calls,checksum"
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
                    let start = DWT::cycle_count();
                    let result = run(implementation, mode, data, repeats, domain.special);
                    let ticks = DWT::cycle_count().wrapping_sub(start);
                    if round >= 5 {
                        writeln!(
                            payload,
                            "{implementation:?},{},{mode:?},{},{ticks},{hz},{},{:016x}",
                            domain.name,
                            round - 5,
                            result.calls,
                            result.checksum
                        )?;
                    }
                    poll();
                }
            }
        }
    }
    writeln!(
        payload,
        "ACCURACY\ntest_distribution,index,x_bits,y_bits,baseline_bits,candidate_bits"
    )?;
    for domain in DOMAINS {
        for (i, pair) in cases(domain).iter().enumerate() {
            let x = f64::from_bits(pair.x);
            let y = f64::from_bits(pair.y);
            let a = value(Implementation::Baseline, x, y).to_bits();
            let b = value(Implementation::Candidate, x, y).to_bits();
            writeln!(
                payload,
                "{},{i},{:016x},{:016x},{a:016x},{b:016x}",
                domain.name, pair.x, pair.y
            )?;
            poll();
        }
    }
    Ok(())
}

fn calibrate(data: &[pow_bench_core::Case], mode: Mode, special: bool) -> u32 {
    let mut repeats = 1u32;
    while repeats < 4096 {
        let start = DWT::cycle_count();
        run(Implementation::Baseline, mode, data, repeats, special);
        if DWT::cycle_count().wrapping_sub(start) >= 100_000 {
            break;
        }
        repeats *= 2;
    }
    repeats
}
