// Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.
// Developed at SunPro, a Sun Microsystems, Inc. business.
// Permission to use, copy, modify, and distribute this software is freely
// granted, provided that this notice is preserved.

extern crate core;

use self::core::f64::consts::{E, PI};
use super::pow;

const POS_ZERO: &[f64] = &[0.0];
const NEG_ZERO: &[f64] = &[-0.0];
const POS_ONE: &[f64] = &[1.0];
const NEG_ONE: &[f64] = &[-1.0];
const POS_FLOATS: &[f64] = &[99.0 / 70.0, E, PI];
const NEG_FLOATS: &[f64] = &[-99.0 / 70.0, -E, -PI];
const POS_SMALL_FLOATS: &[f64] = &[(1.0 / 2.0), f64::MIN_POSITIVE, f64::EPSILON];
const NEG_SMALL_FLOATS: &[f64] = &[-(1.0 / 2.0), -f64::MIN_POSITIVE, -f64::EPSILON];
const POS_EVENS: &[f64] = &[2.0, 6.0, 8.0, 10.0, 22.0, 100.0, f64::MAX];
const NEG_EVENS: &[f64] = &[f64::MIN, -100.0, -22.0, -10.0, -8.0, -6.0, -2.0];
const POS_ODDS: &[f64] = &[3.0, 7.0];
const NEG_ODDS: &[f64] = &[-7.0, -3.0];
const NANS: &[f64] = &[f64::NAN];
const POS_INF: &[f64] = &[f64::INFINITY];
const NEG_INF: &[f64] = &[f64::NEG_INFINITY];

const ALL: &[&[f64]] = &[
    POS_ZERO,
    NEG_ZERO,
    NANS,
    NEG_SMALL_FLOATS,
    POS_SMALL_FLOATS,
    NEG_FLOATS,
    POS_FLOATS,
    NEG_EVENS,
    POS_EVENS,
    NEG_ODDS,
    POS_ODDS,
    NEG_INF,
    POS_INF,
    NEG_ONE,
    POS_ONE,
];
const POS: &[&[f64]] = &[POS_ZERO, POS_ODDS, POS_ONE, POS_FLOATS, POS_EVENS, POS_INF];
const NEG: &[&[f64]] = &[NEG_ZERO, NEG_ODDS, NEG_ONE, NEG_FLOATS, NEG_EVENS, NEG_INF];

fn pow_test(base: f64, exponent: f64, expected: f64) {
    let res = pow(base, exponent);
    assert!(
        if expected.is_nan() {
            res.is_nan()
        } else {
            res.to_bits() == expected.to_bits()
        },
        "{base} ** {exponent} was {res} instead of {expected}",
    );
}

fn test_sets_as_base(sets: &[&[f64]], exponent: f64, expected: f64) {
    sets.iter()
        .for_each(|s| s.iter().for_each(|val| pow_test(*val, exponent, expected)));
}

fn test_sets_as_exponent(base: f64, sets: &[&[f64]], expected: f64) {
    sets.iter()
        .for_each(|s| s.iter().for_each(|val| pow_test(base, *val, expected)));
}

fn test_sets(sets: &[&[f64]], computed: &dyn Fn(f64) -> f64, expected: &dyn Fn(f64) -> f64) {
    sets.iter().for_each(|s| {
        s.iter().for_each(|val| {
            let exp = expected(*val);
            let res = computed(*val);

            #[cfg(x86_no_sse2)]
            let exp = force_eval!(exp);
            #[cfg(x86_no_sse2)]
            let res = force_eval!(res);
            assert!(
                if exp.is_nan() {
                    res.is_nan()
                } else {
                    exp == res
                },
                "test for {val} was {res} instead of {exp}",
            );
        })
    });
}

#[test]
fn zero_as_exponent() {
    test_sets_as_base(ALL, 0.0, 1.0);
    test_sets_as_base(ALL, -0.0, 1.0);
}

#[test]
fn one_as_base() {
    test_sets_as_exponent(1.0, ALL, 1.0);
}

#[test]
fn nan_inputs() {
    test_sets_as_exponent(f64::NAN, &ALL[2..], f64::NAN);

    test_sets_as_base(&ALL[..(ALL.len() - 2)], f64::NAN, f64::NAN);
}

#[test]
fn infinity_as_base() {
    test_sets_as_exponent(f64::INFINITY, &POS[1..], f64::INFINITY);

    test_sets_as_exponent(f64::INFINITY, &NEG[1..], 0.0);

    test_sets_as_exponent(f64::NEG_INFINITY, &[POS_ODDS], f64::NEG_INFINITY);

    test_sets(ALL, &|v: f64| pow(f64::NEG_INFINITY, v), &|v: f64| {
        pow(-0.0, -v)
    });
}

#[test]
fn infinity_as_exponent() {
    test_sets_as_base(&ALL[5..(ALL.len() - 2)], f64::INFINITY, f64::INFINITY);

    test_sets_as_base(&ALL[5..ALL.len() - 2], f64::NEG_INFINITY, 0.0);

    let base_below_one = &[POS_ZERO, NEG_ZERO, NEG_SMALL_FLOATS, POS_SMALL_FLOATS];

    test_sets_as_base(base_below_one, f64::INFINITY, 0.0);

    test_sets_as_base(base_below_one, f64::NEG_INFINITY, f64::INFINITY);

    test_sets_as_base(&[NEG_ONE, POS_ONE], f64::INFINITY, 1.0);

    test_sets_as_base(&[NEG_ONE, POS_ONE], f64::NEG_INFINITY, 1.0);
}

#[test]
fn zero_as_base() {
    test_sets_as_exponent(0.0, &POS[1..], 0.0);

    test_sets_as_exponent(0.0, &NEG[1..], f64::INFINITY);

    test_sets_as_exponent(-0.0, &POS[3..], 0.0);

    test_sets_as_exponent(-0.0, &NEG[3..], f64::INFINITY);

    test_sets_as_exponent(-0.0, &[POS_ODDS], -0.0);

    test_sets_as_exponent(-0.0, &[NEG_ODDS], f64::NEG_INFINITY);
}

#[test]
fn special_cases() {
    test_sets(ALL, &|v: f64| pow(v, 1.0), &|v: f64| v);

    test_sets(ALL, &|v: f64| pow(v, -1.0), &|v: f64| 1.0 / v);

    [POS_ZERO, NEG_ZERO, POS_ONE, NEG_ONE, POS_EVENS, NEG_EVENS]
        .iter()
        .for_each(|int_set| {
            int_set.iter().for_each(|int| {
                test_sets(ALL, &|v: f64| pow(-v, *int), &|v: f64| {
                    pow(-1.0, *int) * pow(v, *int)
                });
            })
        });

    NEG[1..(NEG.len() - 1)].iter().for_each(|set| {
        set.iter().for_each(|val| {
            test_sets(&ALL[3..7], &|v: f64| pow(*val, v), &|_| f64::NAN);
        })
    });
}

#[test]
fn normal_cases() {
    assert_eq!(pow(2.0, 20.0), (1 << 20) as f64);
    assert_eq!(pow(-1.0, 9.0), -1.0);
    assert!(pow(-1.0, 2.2).is_nan());
    assert!(pow(-1.0, -1.14).is_nan());
}

#[test]
fn signed_underflow_and_nan_identities() {
    for nan in [f64::NAN, f64::from_bits(0x7ff0000000000001)] {
        assert_eq!(pow(1.0, nan), 1.0);
        assert_eq!(pow(nan, 0.0), 1.0);
        assert_eq!(pow(nan, -0.0), 1.0);
    }
    assert_eq!(pow(-2.0, -1075.0).to_bits(), (-0.0f64).to_bits());
    assert_eq!(pow(-f64::from_bits(1), 3.0).to_bits(), (-0.0f64).to_bits());
    assert_eq!(pow(f64::MAX, 1.0), f64::MAX);
    assert_eq!(pow(f64::from_bits(1), 1.0).to_bits(), 1);
}

#[test]
fn subnormal_log_reduction() {
    let x = f64::from_bits(0x0000ec140bff07ec);
    let y = f64::from_bits(0x3fd405f374d3e30c);
    // The MPFR-rounded result allows one adjacent representation.
    let reference = 0x2bdf3fea5d20a749u64;
    assert!(pow(x, y).to_bits().abs_diff(reference) <= 1);
}
