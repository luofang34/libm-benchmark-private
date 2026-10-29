/* Copyright (c) 2018-2026, Arm Limited. SPDX-License-Identifier: MIT */
#include <stdio.h>
#include "math_config.h"
static void number(const char *name, double x) {
  printf("pub(super) const %s: f64 = %.17e;\n", name, x);
}
int main(void) {
  puts("// Copyright (c) 2018-2026, Arm Limited. SPDX-License-Identifier: MIT\n// Generated from the compiled ARM tables by experiments/pow/dump_tables.c.");
  number("LN2_HI", __pow_log_data.ln2hi); number("LN2_LO", __pow_log_data.ln2lo);
  number("INV_LN2_N", __exp_data.invln2N); number("NEG_LN2_HI_N", __exp_data.negln2hiN);
  number("NEG_LN2_LO_N", __exp_data.negln2loN); number("SHIFT", __exp_data.shift);
  puts("pub(super) const LOG_POLY: [f64; 7] = [");
  for (int i=0;i<7;i++) printf("%.17e,\n",__pow_log_data.poly[i]);
  puts("];\npub(super) const EXP_POLY: [f64; 4] = [");
  for (int i=0;i<4;i++) printf("%.17e,\n",__exp_data.poly[i]);
  puts("];\n#[rustfmt::skip]\npub(super) const LOG_TAB: [[u64; 3]; 128] = [");
  for (int i=0;i<128;i++) printf("[0x%016llx, 0x%016llx, 0x%016llx],\n", (unsigned long long)asuint64(__pow_log_data.tab[i].invc), (unsigned long long)asuint64(__pow_log_data.tab[i].logc), (unsigned long long)asuint64(__pow_log_data.tab[i].logctail));
  puts("];\n#[rustfmt::skip]\npub(super) const EXP_TAB: [[u64; 2]; 128] = [");
  for (int i=0;i<128;i++) printf("[0x%016llx, 0x%016llx],\n",(unsigned long long)__exp_data.tab[2*i],(unsigned long long)__exp_data.tab[2*i+1]);
  puts("];");
}
