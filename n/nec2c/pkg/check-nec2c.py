#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 AerynOS Developers
# SPDX-License-Identifier: MPL-2.0
"""Check phase for nec2c.

Upstream ships no test suite, so this does two things:

1. A physics check. It sweeps a thin dipole through resonance and checks the
   resonant length and feedpoint resistance against the textbook values for a
   thin resonant dipole (about 0.475 wavelengths, about 70 ohms). The expected
   numbers come from antenna theory rather than from a previous nec2c run, so
   this is a real validation of the numerical core and not a recording of
   whatever the build happened to produce.

2. A regression sweep. It runs every reference deck in Input/ and checks that
   exactly the expected set succeeds. Deviation either way is an error: a new
   failure means the build broke something, and an unexpected success means
   upstream fixed a deck and this list needs updating.
"""

import pathlib
import re
import subprocess
import sys

# Decks in Input/ that nec2c itself rejects. This is upstream behaviour, not
# something this build introduces: each was confirmed to fail identically under
# both clang -O2 and gcc -O0.
#
#   RP_FR, RP_FS, RP_GR  Not standalone decks at all. They hold only FR/RP/PT
#                        control cards, meant to be appended to a geometry
#                        file, so nec2c reaches the solver with no structure
#                        and fails allocating the interaction matrix.
#   CAR.NEC              A WIREGRID export whose own header notes it has
#                        "commas inserted after the GW terms"; the parser
#                        rejects it.
#   EX6.nec              Rejected at the EX card with "NON-NUMERICAL CHARACTER
#                        '.' IN INTEGER FIELD" - a real number in a field
#                        nec2c reads as an integer.
#   LOGPERIO.NEC         Rejected with "GEOMETRY DATA CARD ERROR", the parser
#                        having reached the geometry stage still looking at the
#                        leading CM comment block.
EXPECTED_FAILURES = {
    "CAR.NEC",
    "EX6.nec",
    "LOGPERIO.NEC",
    "RP_FR",
    "RP_FS",
    "RP_GR",
}

# Physical length of the wire in dipole-sweep.nec, in metres.
DIPOLE_LENGTH_M = 0.5

# A thin resonant dipole is about 0.47-0.48 wavelengths long and shows roughly
# 70 ohms at the feedpoint. The bounds are wide enough not to trip on compiler
# or libm differences, and far too tight to pass if the solver is broken.
RESONANT_LENGTH_RANGE = (0.470, 0.480)
RESONANT_RESISTANCE_RANGE = (65.0, 78.0)

FLOAT = re.compile(r"[-+]?\d+\.\d+E[-+]\d+")


# nec2c stores the input and output file names in fixed 80-char buffers and
# rejects anything longer than this outright, with exit(-1) and no message:
#
#     case 'i': if( strlen(optarg) > 75 ) abort_on_error(-1);
#
# So every deck is run from inside its own directory and named by basename.
# Passing absolute paths instead would silently couple this check to how deep
# the build tree happens to sit: renaming the source tarball was enough to push
# the two longest deck names over the limit and "fail" two decks that are fine.
NEC2C_PATH_MAX = 75


def run(nec2c, cwd, deck, out):
    for name in (deck, out):
        if len(name) > NEC2C_PATH_MAX:
            sys.exit(
                f"check: '{name}' is {len(name)} characters, over nec2c's "
                f"{NEC2C_PATH_MAX}-character limit; run it from a shorter path"
            )
    return subprocess.run(
        [nec2c, "-i", deck, "-o", out],
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode


def parse_sweep(path):
    """Yield (wavelength_m, resistance, reactance) for each frequency step.

    The report repeats one block per frequency. Rather than matching the data
    row by its leading whitespace, which several other tables in the report
    share, this tracks which section it is in and reads the first row after the
    ANTENNA INPUT PARAMETERS heading.
    """
    wavelength = None
    pending = False
    for line in path.read_text(errors="replace").splitlines():
        if "WAVELENGTH:" in line:
            wavelength = float(FLOAT.search(line).group())
        elif "ANTENNA INPUT PARAMETERS" in line:
            pending = True
        elif pending:
            # TAG SEG then nine floats: voltage re/im, current re/im,
            # impedance re/im, admittance re/im, power. Pulled out by regex
            # rather than split() because these are fixed-width Fortran-style
            # columns and adjacent values can run together. The two heading
            # lines under the title contain no floats, so they fall through.
            values = FLOAT.findall(line)
            if not values:
                continue
            if len(values) != 9:
                sys.exit(f"check: expected 9 values in '{line.strip()}', got {len(values)}")
            if wavelength is None:
                sys.exit("check: impedance row appeared before any WAVELENGTH line")
            pending = False
            yield wavelength, float(values[4]), float(values[5])


def check_resonance(nec2c, deck, workdir):
    # Staged next to its output for the same path-length reason as the decks.
    staged = workdir / deck.name
    staged.write_bytes(deck.read_bytes())
    out = workdir / "dipole-sweep.out"
    rc = run(nec2c, workdir, staged.name, out.name)
    if rc != 0:
        sys.exit(f"check: nec2c failed on the dipole sweep with rc={rc}")

    points = list(parse_sweep(out))
    if len(points) < 2:
        sys.exit(f"check: parsed {len(points)} frequency steps from the sweep, expected 21")

    # Find the step where reactance crosses zero and interpolate between the
    # bracketing points.
    for (lam_a, r_a, x_a), (lam_b, r_b, x_b) in zip(points, points[1:]):
        if x_a <= 0.0 <= x_b:
            span = x_b - x_a
            frac = 0.0 if span == 0.0 else -x_a / span
            wavelength = lam_a + frac * (lam_b - lam_a)
            resistance = r_a + frac * (r_b - r_a)
            break
    else:
        reactances = ", ".join(f"{x:.1f}" for _, _, x in points)
        sys.exit(f"check: reactance never crossed zero over the sweep: [{reactances}]")

    length = DIPOLE_LENGTH_M / wavelength
    print(f"resonance: {length:.4f} wavelengths, R = {resistance:.2f} ohms")

    lo, hi = RESONANT_LENGTH_RANGE
    if not lo <= length <= hi:
        sys.exit(f"check: resonant length {length:.4f} wavelengths outside [{lo}, {hi}]")
    lo, hi = RESONANT_RESISTANCE_RANGE
    if not lo <= resistance <= hi:
        sys.exit(f"check: resonant resistance {resistance:.2f} ohms outside [{lo}, {hi}]")


def check_reference_decks(nec2c, inputdir, workdir):
    decks = sorted(p for p in inputdir.iterdir() if p.is_file())
    if not decks:
        sys.exit(f"check: no reference decks found in {inputdir}")

    # Each deck is copied next to the output and run from there. For some cards
    # nec2c writes a companion .plt plot file alongside its input, so running
    # the decks where they lie would scatter generated files through the source
    # tree - and, worse, they would be picked up as extra decks on a re-run.
    staging = workdir / "decks"
    staging.mkdir(parents=True, exist_ok=True)
    failed = set()
    for deck in decks:
        staged = staging / deck.name
        staged.write_bytes(deck.read_bytes())
        if run(nec2c, staging, staged.name, "ref.out") != 0:
            failed.add(deck.name)
    print(f"reference decks: {len(decks) - len(failed)}/{len(decks)} solved")

    unexpected = sorted(failed - EXPECTED_FAILURES)
    if unexpected:
        sys.exit(f"check: decks that used to solve now fail: {', '.join(unexpected)}")

    fixed = sorted(EXPECTED_FAILURES - failed)
    if fixed:
        sys.exit(
            "check: decks expected to fail now solve, update EXPECTED_FAILURES: "
            + ", ".join(fixed)
        )


def main():
    nec2c, deck, inputdir, workdir = sys.argv[1:5]
    workdir = pathlib.Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    check_resonance(nec2c, pathlib.Path(deck), workdir)
    check_reference_decks(nec2c, pathlib.Path(inputdir), workdir)
    print("nec2c: all checks passed")


if __name__ == "__main__":
    main()
