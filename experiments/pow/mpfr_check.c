#include <mpfr.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
double arm_pow(double,double);
struct stats { unsigned long count,bins[5],classification,zero_sign,c_difference; double max,x,y,actual,reference; };
static const char *names[]={"libm_old","petir","std","arm_patch","rebuilt_base","rebuilt_patch","arm_c"};
static const char *domains[]={"positive","near_one","negative_integer","subnormal","range_edge","random_bits","log_uniform","table_boundary","adversarial_one","special","all"};
static uint64_t bits(double x) { uint64_t u;memcpy(&u,&x,8);return u; }
static void record(struct stats *s,double x,double y,double a,double ref,double error,double c) {
    s->count++;
    if (isnan(ref)) { s->classification+=!isnan(a); }
    else if (isinf(ref)) { s->classification+=a!=ref; }
    else if (!isfinite(a)) s->classification++;
    else {
        if (ref==0 && a==0 && !!signbit(ref)!=!!signbit(a)) s->zero_sign++;
        int bin= error==0 ? 0 : error<=.5 ? 1 : error<=1 ? 2 : error<=2 ? 3 : 4;
        s->bins[bin]++;
        if(error>s->max) {s->max=error;s->x=x;s->y=y;s->actual=a;s->reference=ref;}
    }
    if (!(isnan(c)&&isnan(a)) && bits(c)!=bits(a)) s->c_difference++;
}
int main(int argc,char **argv) {
    if(argc!=3) return 2;
    FILE *input=fopen(argv[1],"rb"),*labels=fopen(argv[2],"r");
    if(!input||!labels) return 3;
    mpfr_t x,y,ref,err;mpfr_inits2(256,x,y,ref,err,(mpfr_ptr)0);
    struct stats all[11][7]={0};double row[8];char label[80];
    while(fread(row,sizeof(double),8,input)==8) {
        if(!fgets(label,sizeof(label),labels)) return 4;
        label[strcspn(label,"\r\n")]=0; int domain=0;
        while(domain<10 && strcmp(domains[domain],label)) domain++;
        if(domain==10) return 5;
        mpfr_set_d(x,row[0],MPFR_RNDN);mpfr_set_d(y,row[1],MPFR_RNDN);mpfr_pow(ref,x,y,MPFR_RNDN);
        double expected=mpfr_get_d(ref,MPFR_RNDN),c=arm_pow(row[0],row[1]);
        for(int k=0;k<7;k++) {
            double actual=k==6 ? c : row[k+2], error=0;
            if(isfinite(expected)&&isfinite(actual)) {
                int exponent=(expected==0||fabs(expected)<0x1p-1022) ? -1074 : ilogb(fabs(expected))-52;
                mpfr_set_d(err,actual,MPFR_RNDN);mpfr_sub(err,err,ref,MPFR_RNDN);
                mpfr_abs(err,err,MPFR_RNDN);mpfr_mul_2si(err,err,-exponent,MPFR_RNDN);
                error=mpfr_get_d(err,MPFR_RNDU);
            }
            record(&all[domain][k],row[0],row[1],actual,expected,error,c);
            record(&all[10][k],row[0],row[1],actual,expected,error,c);
        }
    }
    printf("domain,implementation,count,max_ulp,exact,le_half_ulp,le_one_ulp,le_two_ulp,gt_two_ulp,class_mismatch,signed_zero_mismatch,arm_c_bit_difference,worst_x,worst_y,worst_actual,worst_reference\n");
    for(int d=0;d<11;d++) for(int k=0;k<7;k++) {
        struct stats s=all[d][k];
        printf("%s,%s,%lu,%.17g,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%a,%a,%a,%a\n",domains[d],names[k],s.count,s.max,s.bins[0],s.bins[1],s.bins[2],s.bins[3],s.bins[4],s.classification,s.zero_sign,s.c_difference,s.x,s.y,s.actual,s.reference);
    }
    fprintf(stderr,"MPFR %s; precision=256; rounding=nearest; samples=%lu\n",mpfr_get_version(),all[10][0].count);
    mpfr_clears(x,y,ref,err,(mpfr_ptr)0);fclose(input);fclose(labels);
}
