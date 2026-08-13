"""Post-build check for the packaged scipy.

scipy.test() needs pytest and hypothesis, neither of which AerynOS packages, so
the upstream suite cannot run here. This exercises the parts most likely to be
broken by packaging: that the compiled extensions import, that the BLAS/LAPACK
backend is real, and that the Fortran-heavy code paths give correct answers.
"""

import sys

import numpy as np
import scipy
from scipy import fft, integrate, linalg, optimize, sparse

print("scipy", scipy.__version__, "on numpy", np.__version__)

cfg = scipy.show_config(mode="dicts")
blas = cfg["Build Dependencies"]["blas"]
print("blas:", blas["name"], blas.get("version"))
if blas["name"] in ("unknown", None):
    sys.exit("scipy was built without a real BLAS backend")

# LAPACK through the Fortran bindings.
a = np.array([[4.0, 1.0], [1.0, 3.0]])
b = np.array([1.0, 2.0])
x = linalg.solve(a, b)
assert np.allclose(a @ x, b), x

lu, piv = linalg.lu_factor(a)
assert np.allclose(linalg.lu_solve((lu, piv), b), x)

# Root finding and minimisation.
root = optimize.brentq(lambda t: t**2 - 2.0, 0.0, 2.0)
assert abs(root - np.sqrt(2.0)) < 1e-12, root

# Quadrature.
area, err = integrate.quad(np.sin, 0.0, np.pi)
assert abs(area - 2.0) < 1e-9, (area, err)

# pocketfft round trip.
sig = np.array([1.0, 2.0, 3.0, 4.0])
assert np.allclose(fft.ifft(fft.fft(sig)).real, sig)

# Sparse matrices, which have their own compiled core.
m = sparse.csr_matrix(a)
assert np.allclose(m.dot(x), b)

print("lapack, optimize, quad, fft and sparse paths all agree")
