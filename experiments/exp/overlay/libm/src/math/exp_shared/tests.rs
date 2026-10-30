use super::super::{exp, exp2};

#[test]
fn exponential_special_values() {
    for function in [exp as fn(f64) -> f64, exp2] {
        for zero in [0.0, -0.0] {
            assert_eq!(function(zero).to_bits(), 1.0f64.to_bits());
        }
        assert_eq!(function(f64::INFINITY), f64::INFINITY);
        assert_eq!(function(f64::NEG_INFINITY).to_bits(), 0);
        for bits in [0x7ff8_0000_0000_0001, 0x7ff0_0000_0000_0001] {
            assert!(function(f64::from_bits(bits)).is_nan());
        }
    }
    assert_eq!(exp(1000.0), f64::INFINITY);
    assert_eq!(exp(-1000.0).to_bits(), 0);
    assert_eq!(exp2(1024.0), f64::INFINITY);
    assert_eq!(exp2(-1075.0).to_bits(), 0);
}

#[test]
fn exp2_integer_powers_are_exact() {
    for exponent in -1074..=1023 {
        let expected = if exponent < -1022 {
            1u64 << (exponent + 1074)
        } else {
            ((exponent + 1023) as u64) << 52
        };
        assert_eq!(exp2(f64::from(exponent)).to_bits(), expected);
    }
}

#[test]
fn exp2_negative_table_boundary() {
    assert_eq!(exp2(-3.0 / 256.0).to_bits(), 0x3fef_bdba_3692_d514);
}
