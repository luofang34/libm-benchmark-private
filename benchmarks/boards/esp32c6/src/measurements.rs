use core::fmt::Write;

use heapless::String;
use pow_bench_core::{DOMAINS, Implementation, Mode, cases, run, value};

use crate::hardware::{cycle_count, elapsed, micros};

pub type Payload = String<131072>;

pub fn measure(
    payload: &mut Payload,
    hz: u32,
    mut poll: impl FnMut(),
) -> Result<u32, core::fmt::Error> {
    let mut maximum = 0;
    writeln!(
        payload,
        "TIMING\nimplementation,test_distribution,mode,round,ticks,timer_hz,calls,checksum,batch_us"
    )?;
    for domain in DOMAINS {
        let data = cases(domain);
        for mode in [Mode::Throughput, Mode::Dependency] {
            let repeats = calibrate(data, mode, domain.special)?;
            for round in 0..20u32 {
                for offset in 0..2u32 {
                    let implementation = if (round + offset) % 2 == 0 {
                        Implementation::Baseline
                    } else {
                        Implementation::Candidate
                    };
                    let before = micros();
                    let start = cycle_count();
                    let result = run(implementation, mode, data, repeats, domain.special);
                    let ticks = elapsed(start);
                    let micros = micros().wrapping_sub(before);
                    check_interval(ticks, micros, hz)?;
                    maximum = maximum.max(micros);
                    if round >= 5 {
                        writeln!(
                            payload,
                            "{implementation:?},{},{mode:?},{},{ticks},{hz},{},{:016x},{micros}",
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
    Ok(maximum)
}

fn calibrate(
    data: &[pow_bench_core::Case],
    mode: Mode,
    special: bool,
) -> Result<u32, core::fmt::Error> {
    let mut repeats = 1u32;
    while repeats < 4096 {
        let before = micros();
        let start = cycle_count();
        run(Implementation::Baseline, mode, data, repeats, special);
        let ticks = elapsed(start);
        check_interval(ticks, micros().wrapping_sub(before), 160_000_000)?;
        if ticks >= 100_000 {
            break;
        }
        repeats *= 2;
    }
    Ok(repeats)
}

fn check_interval(ticks: u32, micros: u32, hz: u32) -> core::fmt::Result {
    // The independent microsecond timer rejects ambiguous 32-bit cycle-counter wraps.
    if micros == 0 || micros >= 100_000 {
        return Err(core::fmt::Error);
    }
    let expected = micros * (hz / 1_000_000);
    if ticks.abs_diff(expected) > 512.max(expected / 50) {
        return Err(core::fmt::Error);
    }
    Ok(())
}
