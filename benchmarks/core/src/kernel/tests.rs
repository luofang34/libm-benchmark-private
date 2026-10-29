use super::*;
use crate::{DOMAINS, cases};

#[test]
fn consumes_remainder_and_every_repeat() {
    let data = [Case {
        x: 2.0f64.to_bits(),
        y: 3.0f64.to_bits(),
    }; 7];
    for implementation in [Implementation::Baseline, Implementation::Candidate] {
        let output = run(implementation, Mode::Throughput, &data, 3, false);
        assert_eq!(output.calls, 21);
        assert_eq!(output.checksum, 8.0f64.to_bits().wrapping_mul(21));
    }
}

#[test]
fn empty_batch_never_divides_by_zero() {
    assert_eq!(
        run(Implementation::Candidate, Mode::Dependency, &[], 2, true),
        Outcome {
            checksum: 0,
            calls: 0
        }
    );
}

#[test]
fn feedback_matches_scalar_execution() {
    for domain in DOMAINS {
        let data = cases(domain);
        for implementation in [Implementation::Baseline, Implementation::Candidate] {
            let mut previous = 0u64;
            let mut sum = 0u64;
            for (i, case) in data.iter().enumerate() {
                let pair = if domain.special {
                    data[(i + (previous as usize & 15)) % data.len()]
                } else {
                    Case {
                        x: case.x ^ (previous & 255),
                        y: case.y,
                    }
                };
                previous = value(
                    implementation,
                    f64::from_bits(pair.x),
                    f64::from_bits(pair.y),
                )
                .to_bits();
                sum = sum.wrapping_add(previous);
            }
            let actual = run(implementation, Mode::Dependency, data, 1, domain.special);
            assert_eq!(actual.checksum, sum);
        }
    }
}

#[test]
fn ieee_identities_and_signed_zero() {
    for implementation in [Implementation::Baseline, Implementation::Candidate] {
        assert_eq!(
            value(implementation, -0.0, 3.0).to_bits(),
            (-0.0f64).to_bits()
        );
        assert_eq!(value(implementation, -0.0, -3.0), f64::NEG_INFINITY);
        assert_eq!(
            value(implementation, f64::from_bits(0x7ff0000000000001), 0.0),
            1.0
        );
    }
}
