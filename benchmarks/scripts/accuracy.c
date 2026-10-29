#include <mpfr.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

struct stats {
    uint64_t count, classes, zeros, bins[5];
    double maximum;
    uint64_t x, y, actual, reference;
};
static const char *domains[] = {"positive", "near_one", "magnitude", "negative_integer",
                               "subnormal", "range_edge", "special", "all"};
static double number(uint64_t bits) { double x; memcpy(&x, &bits, 8); return x; }
static uint64_t bits(double x) { uint64_t b; memcpy(&b, &x, 8); return b; }

static void record(struct stats *s, uint64_t x, uint64_t y, double a, double ref, double ulp) {
    s->count++;
    if (isnan(ref)) s->classes += !isnan(a);
    else if (isinf(ref)) s->classes += a != ref;
    else if (!isfinite(a)) s->classes++;
    else {
        if (ref == 0 && a == 0) s->zeros += !!signbit(a) != !!signbit(ref);
        s->bins[ulp == 0 ? 0 : ulp <= .5 ? 1 : ulp <= 1 ? 2 : ulp <= 2 ? 3 : 4]++;
        if (ulp > s->maximum) {
            s->maximum = ulp; s->x = x; s->y = y;
            s->actual = bits(a); s->reference = bits(ref);
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 2) return 2;
    FILE *input = fopen(argv[1], "r");
    if (!input) return 3;
    char line[512], domain[64];
    if (!fgets(line, sizeof line, input)) return 4;
    mpfr_t x, y, ref, error;
    mpfr_inits2(256, x, y, ref, error, (mpfr_ptr)0);
    struct stats all[8][2] = {0};
    while (fgets(line, sizeof line, input)) {
        unsigned int index; unsigned long long xb, yb, ab[2];
        if (sscanf(line, "%63[^,],%u,%llx,%llx,%llx,%llx", domain, &index, &xb, &yb, &ab[0], &ab[1]) != 6) return 5;
        int d = 0;
        while (d < 7 && strcmp(domain, domains[d])) d++;
        if (d == 7) return 6;
        mpfr_set_d(x, number(xb), MPFR_RNDN); mpfr_set_d(y, number(yb), MPFR_RNDN);
        mpfr_pow(ref, x, y, MPFR_RNDN);
        double expected = mpfr_get_d(ref, MPFR_RNDN);
        for (int k = 0; k < 2; k++) {
            double actual = number(ab[k]), ulp = 0;
            if (isfinite(expected) && isfinite(actual)) {
                int exponent = fabs(expected) < 0x1p-1022 ? -1074 : ilogb(fabs(expected)) - 52;
                mpfr_set_d(error, actual, MPFR_RNDN); mpfr_sub(error, error, ref, MPFR_RNDN);
                mpfr_abs(error, error, MPFR_RNDN); mpfr_mul_2si(error, error, -exponent, MPFR_RNDN);
                ulp = mpfr_get_d(error, MPFR_RNDU);
            }
            record(&all[d][k], xb, yb, actual, expected, ulp);
            record(&all[7][k], xb, yb, actual, expected, ulp);
        }
    }
    if (ferror(input) || all[7][0].count == 0) return 7;
    puts("test_distribution,implementation,cases,accuracy_max_ulp,class_mismatch,signed_zero_mismatch,exact,le_half_ulp,le_one_ulp,le_two_ulp,gt_two_ulp,worst_x,worst_y,worst_actual,worst_reference");
    int failed = 0;
    for (int d = 0; d < 8; d++) for (int k = 0; k < 2; k++) {
        struct stats s = all[d][k];
        printf("%s,%s,%llu,%.17g,%llu,%llu,%llu,%llu,%llu,%llu,%llu,%016llx,%016llx,%016llx,%016llx\n",
               domains[d], k ? "Candidate" : "Baseline", (unsigned long long)s.count, s.maximum,
               (unsigned long long)s.classes, (unsigned long long)s.zeros,
               (unsigned long long)s.bins[0], (unsigned long long)s.bins[1], (unsigned long long)s.bins[2],
               (unsigned long long)s.bins[3], (unsigned long long)s.bins[4],
               (unsigned long long)s.x, (unsigned long long)s.y,
               (unsigned long long)s.actual, (unsigned long long)s.reference);
        failed |= s.classes || s.zeros || s.maximum > 1;
    }
    fprintf(stderr, "MPFR %s; precision=256; rounding=nearest; samples=%llu\n", mpfr_get_version(), (unsigned long long)all[7][0].count);
    mpfr_clears(x, y, ref, error, (mpfr_ptr)0); fclose(input);
    return failed;
}

