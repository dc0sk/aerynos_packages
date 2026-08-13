"""Post-build check for the packaged hypothesis.

The upstream suite needs a long list of extra plugins, so instead this checks
what numpy and scipy actually depend on: that the module imports (including its
compiled rust extension), that the engine generates cases, and that it shrinks
a failure to the documented minimal example.
"""

import hypothesis
from hypothesis import given, settings
from hypothesis import strategies as st

print("hypothesis", hypothesis.__version__)

seen = []


@given(st.integers())
@settings(max_examples=25, database=None)
def collects(value):
    seen.append(value)


collects()
assert len(seen) >= 10, f"engine only produced {len(seen)} examples"

# A property that fails for any value over 100 must shrink to exactly 101.
falsifying = []


@given(st.integers(min_value=0))
@settings(database=None)
def under_a_hundred(value):
    if value > 100:
        falsifying.append(value)
        raise AssertionError(value)


try:
    under_a_hundred()
except AssertionError:
    pass
else:
    raise SystemExit("hypothesis failed to find a falsifying example")

assert min(falsifying) == 101, f"shrinking stopped at {min(falsifying)}, expected 101"

print(f"generated {len(seen)} examples and shrank the failure to 101")
