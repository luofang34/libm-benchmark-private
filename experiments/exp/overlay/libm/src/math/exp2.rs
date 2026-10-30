// Copyright (c) 2018-2025, Arm Limited.
// SPDX-License-Identifier: MIT
/*
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
use super::exp_shared::specialcase;
use super::exp_shared::table::{EXP_TAB, EXP2_POLY as C, EXP2_SHIFT as SHIFT};

/// Returns 2 raised to the power of `x` (f64).
#[cfg_attr(assert_no_panic, no_panic::no_panic)]
pub fn exp2(x: f64) -> f64 {
    let bits = x.to_bits();
    let abstop = ((bits >> 52) as u32) & 0x7ff;
    if abstop < 0x3c9 {
        return 1.0 + x;
    }
    if abstop >= 0x409 {
        if bits == f64::NEG_INFINITY.to_bits() {
            return 0.0;
        }
        if abstop >= 0x7ff {
            return 1.0 + x;
        }
        if bits >> 63 == 0 {
            return f64::INFINITY;
        }
        if bits >= (-1075.0f64).to_bits() {
            return 0.0;
        }
    }
    let kd = x + SHIFT;
    let ki = kd.to_bits();
    let kd = kd - SHIFT;
    let r = x - kd;
    let row = EXP_TAB[(ki & 127) as usize];
    let sbits = row[1].wrapping_add(ki.wrapping_shl(45));
    let r2 = r * r;
    let tmp =
        f64::from_bits(row[0]) + r * C[0] + r2 * (C[1] + r * C[2]) + r2 * r2 * (C[3] + r * C[4]);
    if bits.wrapping_mul(2) > 928.0f64.to_bits() * 2 {
        specialcase(tmp, sbits, ki, 1)
    } else {
        let scale = f64::from_bits(sbits);
        scale + scale * tmp
    }
}
