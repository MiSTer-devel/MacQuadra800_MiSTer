/* fp_attribution 2026-10-24: a radix-2 complex FFT on doubles in memory.
 *
 * The Numerical Recipes four1 structure (bit reversal, then the
 * Danielson-Lanczos butterflies with the twiddle recurrence) on N complex
 * doubles in two static arrays.  Every double -- the arrays, the butterfly
 * temporaries and the twiddles -- is volatile, so each statement loads its
 * operands from memory and stores its result there, which is how a 1990s
 * Macintosh compiler laid out doubles.  sin() for the per-stage twiddle seed
 * is a short series (no libm).
 *
 * REPS forward+inverse pairs run between the two stamps; the inverse is
 * scaled by 1/N, so at the end the data must equal the input to 1e-9.
 */
extern void stamp(void);

#ifndef N
#define N 256
#endif
#ifndef REPS
#define REPS 1
#endif

#define PI 3.14159265358979323846

static volatile double re[N], im[N];
static double x0re[N], x0im[N];

static double dabs(double x) { return x < 0.0 ? -x : x; }

/* sin x for |x| <= pi: fold to |x| <= pi/2, then the series to x^19
   (error below 1e-15) */
static double sin_s(double x)
{
	double z, p;
	if (x > PI / 2) x = PI - x;
	else if (x < -PI / 2) x = -PI - x;
	z = x * x;
	p = x * (1.0 + z * (-1.0 / 6 + z * (1.0 / 120 + z * (-1.0 / 5040 + z * (1.0 / 362880 +
	    z * (-1.0 / 39916800 + z * (1.0 / 6227020800.0 + z * (-1.0 / 1307674368000.0 +
	    z * (1.0 / 355687428096000.0 + z * (-1.0 / 121645100408832000.0))))))))));
	return p;
}

static void four1(int isign)
{
	int i, j, m, mmax, istep, n = N;
	volatile double tr, ti, wr, wi, wpr, wpi, wtemp, theta;

	/* bit reversal */
	j = 0;
	for (i = 0; i < n - 1; i++) {
		if (i < j) {
			tr = re[i]; ti = im[i];
			re[i] = re[j]; im[i] = im[j];
			re[j] = tr; im[j] = ti;
		}
		m = n >> 1;
		while (m >= 1 && j >= m) { j -= m; m >>= 1; }
		j += m;
	}
	/* Danielson-Lanczos */
	mmax = 1;
	while (mmax < n) {
		istep = mmax << 1;
		theta = (double)isign * (PI / (double)mmax);
		wtemp = sin_s(0.5 * theta);
		wpr = -2.0 * wtemp * wtemp;
		wpi = sin_s(theta);
		wr = 1.0; wi = 0.0;
		for (m = 0; m < mmax; m++) {
			for (i = m; i < n; i += istep) {
				j = i + mmax;
				tr = wr * re[j] - wi * im[j];
				ti = wr * im[j] + wi * re[j];
				re[j] = re[i] - tr;
				im[j] = im[i] - ti;
				re[i] = re[i] + tr;
				im[i] = im[i] + ti;
			}
			wtemp = wr;
			wr = wtemp * wpr - wi * wpi + wr;
			wi = wi * wpr + wtemp * wpi + wi;
		}
		mmax = istep;
	}
}

int main(void)
{
	int i, r;
	unsigned long lcg = 12345;
	double scale, err;

	for (i = 0; i < N; i++) {
		lcg = lcg * 1103515245UL + 12345UL;
		x0re[i] = (double)(long)((lcg >> 8) & 0xFFFF) / 32768.0 - 1.0;
		lcg = lcg * 1103515245UL + 12345UL;
		x0im[i] = (double)(long)((lcg >> 8) & 0xFFFF) / 32768.0 - 1.0;
		re[i] = x0re[i]; im[i] = x0im[i];
	}
	stamp();
	scale = 1.0 / (double)N;
	for (r = 0; r < REPS; r++) {
		four1(1);
		four1(-1);
		for (i = 0; i < N; i++) { re[i] = re[i] * scale; im[i] = im[i] * scale; }
	}
	stamp();
	err = 0.0;
	for (i = 0; i < N; i++) {
		if (dabs(re[i] - x0re[i]) > err) err = dabs(re[i] - x0re[i]);
		if (dabs(im[i] - x0im[i]) > err) err = dabs(im[i] - x0im[i]);
	}
	if (err > 1e-9)
		return 1;
	return 0;
}
