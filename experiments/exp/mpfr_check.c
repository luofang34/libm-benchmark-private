#include <math.h>
#include <mpfr.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

double arm_exp(double);
double arm_exp2(double);
struct stats {
    unsigned long count, bins[5], classification, zero_sign, arm_difference;
    double maximum, input, actual, reference;
};
static const char *names[] = {"libm_base", "libm_candidate", "std", "arm_c"};
static const char *domains[] = {"normal", "near_zero", "subnormal_input", "subnormal_output",
    "range_edge", "random_bits", "wide_finite", "table_boundary", "adversarial_zero", "special", "all"};

static double from_bits(uint64_t bits) { double result; memcpy(&result, &bits, 8); return result; }
static uint64_t to_bits(double value) { uint64_t result; memcpy(&result, &value, 8); return result; }

static void record(struct stats *s, double x, double actual, double reference, double error, double arm) {
    s->count++;
    if (isnan(reference)) s->classification += !isnan(actual);
    else if (isinf(reference)) s->classification += actual != reference;
    else if (!isfinite(actual)) s->classification++;
    else {
        if (reference == 0 && actual == 0) s->zero_sign += !!signbit(reference) != !!signbit(actual);
        int bin = error == 0 ? 0 : error <= .5 ? 1 : error <= 1 ? 2 : error <= 2 ? 3 : 4;
        s->bins[bin]++;
        if (error > s->maximum) {
            s->maximum = error; s->input = x; s->actual = actual; s->reference = reference;
        }
    }
    if (!(isnan(actual) && isnan(arm)) && to_bits(actual) != to_bits(arm)) s->arm_difference++;
}

int main(int argc, char **argv) {
    if (argc != 3) return 2;
    FILE *input = fopen(argv[1], "rb"), *labels = fopen(argv[2], "r");
    if (!input || !labels) return 3;
    mpfr_t x, reference, error;
    mpfr_inits2(256, x, reference, error, (mpfr_ptr)0);
    struct stats all[2][11][4] = {0};
    uint64_t row[5]; char label[80]; size_t bytes_read;
    while ((bytes_read = fread(row, 1, sizeof(row), input)) == sizeof(row)) {
        if (row[0] > 1 || !fgets(label, sizeof(label), labels)) return 4;
        label[strcspn(label, "\r\n")] = 0;
        int domain = 0;
        while (domain < 10 && strcmp(domains[domain], label)) domain++;
        if (domain == 10) return 5;
        double value = from_bits(row[1]);
        mpfr_set_d(x, value, MPFR_RNDN);
        if (row[0] == 0) mpfr_exp(reference, x, MPFR_RNDN);
        else mpfr_exp2(reference, x, MPFR_RNDN);
        double expected = mpfr_get_d(reference, MPFR_RNDN);
        double arm = row[0] == 0 ? arm_exp(value) : arm_exp2(value);
        for (int kind = 0; kind < 4; kind++) {
            double actual = kind == 3 ? arm : from_bits(row[kind + 2]), ulps = 0;
            if (isfinite(expected) && isfinite(actual)) {
                int exponent = expected == 0 || fabs(expected) < 0x1p-1022 ? -1074 : ilogb(fabs(expected)) - 52;
                mpfr_set_d(error, actual, MPFR_RNDN);
                mpfr_sub(error, error, reference, MPFR_RNDN);
                mpfr_abs(error, error, MPFR_RNDN);
                mpfr_mul_2si(error, error, -exponent, MPFR_RNDN);
                ulps = mpfr_get_d(error, MPFR_RNDU);
            }
            record(&all[row[0]][domain][kind], value, actual, expected, ulps, arm);
            record(&all[row[0]][10][kind], value, actual, expected, ulps, arm);
        }
    }
    if (bytes_read != 0 || !feof(input) || fgetc(labels) != EOF) return 6;
    printf("function,domain,implementation,count,max_ulp,exact,le_half_ulp,le_one_ulp,le_two_ulp,gt_two_ulp,class_mismatch,signed_zero_mismatch,arm_c_bit_difference,worst_x,worst_actual,worst_reference\n");
    for (int function = 0; function < 2; function++) for (int domain = 0; domain < 11; domain++) for (int kind = 0; kind < 4; kind++) {
        struct stats s = all[function][domain][kind];
        printf("%s,%s,%s,%lu,%.17g,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%a,%a,%a\n",
            function ? "exp2" : "exp", domains[domain], names[kind], s.count, s.maximum,
            s.bins[0], s.bins[1], s.bins[2], s.bins[3], s.bins[4], s.classification,
            s.zero_sign, s.arm_difference, s.input, s.actual, s.reference);
    }
    fprintf(stderr, "MPFR %s; precision=256; rounding=nearest; exp=%lu; exp2=%lu\n",
        mpfr_get_version(), all[0][10][0].count, all[1][10][0].count);
    mpfr_clears(x, reference, error, (mpfr_ptr)0);
    fclose(input); fclose(labels);
    return 0;
}
