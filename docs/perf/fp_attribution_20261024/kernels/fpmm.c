/* fp_attribution 2026-10-24: a Speedometer-shaped double matrix multiply.
 *
 * N x N doubles in static arrays.  The sum accumulates in the result
 * element through a volatile pointer, so every multiply-add is an FP load
 * (FMOVE memory -> register), an FMUL and an FADD with memory sources and
 * an FP store (FMOVE register -> memory): the shape of code whose doubles
 * all live in memory, which is what Speedometer 4's FPU tests compile to.
 * -DREGACC keeps the sum in an FP register across the k loop instead (the
 * modern-compiler shape), for comparison.
 *
 * REPS multiplies run between the two stamps; the per-PC profiles of two
 * REPS counts, differenced, give the steady state.  main returns 0 when the
 * result checks (sum of all elements against the row/column sums, and one
 * element against a direct dot product).
 */
extern void stamp(void);

#ifndef N
#define N 20
#endif
#ifndef REPS
#define REPS 1
#endif

static double a[N][N], b[N][N], c[N][N];

static void mul(void)
{
	int i, j, k;
	for (i = 0; i < N; i++)
		for (j = 0; j < N; j++) {
#ifdef REGACC
			double s = 0.0;
			for (k = 0; k < N; k++)
				s += a[i][k] * b[k][j];
			c[i][j] = s;
#else
			volatile double *cp = &c[i][j];
			*cp = 0.0;
			for (k = 0; k < N; k++)
				*cp += a[i][k] * b[k][j];
#endif
		}
}

static double dabs(double x) { return x < 0.0 ? -x : x; }

int main(void)
{
	int i, j, k, r;
	double s, e, ra, rb;

	for (i = 0; i < N; i++)
		for (j = 0; j < N; j++) {
			a[i][j] = (double)(i + 1) / (double)(j + 2);
			b[i][j] = (double)(j + 1) * 0.25 - (double)i;
		}
	stamp();
	for (r = 0; r < REPS; r++)
		mul();
	stamp();

	/* sum of c = sum_k (sum_i a[i][k]) * (sum_j b[k][j]) */
	s = 0.0;
	for (i = 0; i < N; i++)
		for (j = 0; j < N; j++)
			s += c[i][j];
	e = 0.0;
	for (k = 0; k < N; k++) {
		ra = 0.0; rb = 0.0;
		for (i = 0; i < N; i++) ra += a[i][k];
		for (j = 0; j < N; j++) rb += b[k][j];
		e += ra * rb;
	}
	if (dabs(s - e) > 1e-9 * (dabs(e) > 1.0 ? dabs(e) : 1.0))
		return 1;
	/* one element by a direct dot product in the same order */
	e = 0.0;
	for (k = 0; k < N; k++)
		e += a[3][k] * b[k][5];
	if (dabs(c[3][5] - e) > 1e-9 * (dabs(e) > 1.0 ? dabs(e) : 1.0))
		return 2;
	return 0;
}
