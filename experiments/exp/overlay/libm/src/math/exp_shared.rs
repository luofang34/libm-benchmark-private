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
pub(super) mod table;
#[cfg(test)]
mod tests;

// Scaling in two steps keeps the intermediate normal near the exponent limits.
pub(super) fn specialcase(tmp: f64, sbits: u64, ki: u64, overflow_shift: u64) -> f64 {
    if ki & 0x80000000 == 0 {
        let scale = f64::from_bits(sbits.wrapping_sub(overflow_shift << 52));
        let factor = f64::from_bits((1023 + overflow_shift) << 52);
        return factor * (scale + scale * tmp);
    }
    let scale = f64::from_bits(sbits.wrapping_add(1022u64 << 52));
    let mut y = scale + scale * tmp;
    if y < 1.0 {
        // Round before scaling to avoid double rounding in the subnormal range.
        let lo = scale - y + scale * tmp;
        let hi = 1.0 + y;
        let lo = 1.0 - hi + y + lo;
        y = (hi + lo) - 1.0;
        if y == 0.0 {
            y = 0.0;
        }
    }
    f64::MIN_POSITIVE * y
}
