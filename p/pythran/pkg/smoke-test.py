"""Post-build check for pythran: compile a kernel and run it.

pythran's own suite compiles thousands of cases and takes far too long for a
package build, but simply importing the module would prove almost nothing. The
interesting failure modes here are in the pipeline itself - gast and beniget
parsing the annotated source, the C++ code generation, and the compile against
pythran's bundled headers - so this drives one kernel through all of it and
checks the answer that comes back.
"""

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

KERNEL = """
#pythran export weighted_sum(float list, float list)
def weighted_sum(values, weights):
    return sum(v * w for v, w in zip(values, weights))
"""


def main() -> int:
    import pythran

    print("pythran", pythran.__version__)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        src = tmp / "kernel.py"
        src.write_text(KERNEL)
        out = tmp / "kernel.so"

        proc = subprocess.run(
            [sys.executable, "-m", "pythran.run", str(src), "-o", str(out)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            sys.stderr.write(proc.stdout + proc.stderr)
            return f"pythran failed to compile the kernel (exit {proc.returncode})"
        if not out.exists():
            return "pythran reported success but produced no extension module"

        spec = importlib.util.spec_from_file_location("kernel", out)
        kernel = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(kernel)

        got = kernel.weighted_sum([1.0, 2.0, 3.0], [4.0, 5.0, 6.0])
        expected = 32.0
        assert abs(got - expected) < 1e-9, f"kernel returned {got}, expected {expected}"

    print(f"compiled a kernel and it returned {got}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
