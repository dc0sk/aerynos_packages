"""Post-build check for the packaged numpy.

numpy.test() needs hypothesis, which AerynOS does not package, so the upstream
suite cannot run here. This checks the things packaging is most likely to get
wrong: that the compiled extension modules import at all, that a real BLAS is
linked rather than numpy falling back to something unusable, and that linear
algebra and FFT actually compute correct answers through that backend.
"""

import sys

import numpy as np

print("numpy", np.__version__)

cfg = np.show_config(mode="dicts")
blas = cfg["Build Dependencies"]["blas"]
lapack = cfg["Build Dependencies"]["lapack"]
print("blas:", blas["name"], blas.get("version"))
print("lapack:", lapack["name"], lapack.get("version"))
if blas["name"] in ("unknown", None) or lapack["name"] in ("unknown", None):
    sys.exit("numpy was built without a real BLAS/LAPACK backend")

a = np.array([[3.0, 1.0], [1.0, 2.0]])
b = np.array([9.0, 8.0])
x = np.linalg.solve(a, b)
assert np.allclose(a @ x, b), f"linalg.solve gave {x}"

evals = np.linalg.eigvalsh(a)
assert np.allclose(sorted(evals), sorted(np.linalg.eigvals(a).real)), evals

assert np.allclose(np.fft.ifft(np.fft.fft(b)).real, b), "fft round trip"

print("linalg.solve, eigvalsh and fft round-trips all agree")
