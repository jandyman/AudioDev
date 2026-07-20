
#include <complex.h>

double complex addTwoCmplx(double complex a, double complex b) { return a + b; }

double addTwo(double a, double b) {
    double complex ac = 1 + a * I;
    double complex ab = 1 + b * I;
    return cimag(addTwoCmplx(ac, ab));
}

