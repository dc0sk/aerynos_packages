#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 AerynOS Developers
# SPDX-License-Identifier: MPL-2.0
#
# Build the recipes in this repository and publish the results as a local moss
# repository, so that `moss install ufw` etc. resolve against these packages.
#
# Usage:
#   scripts/local-repo.sh                 # build everything, then index
#   scripts/local-repo.sh u/ufw           # build just these packages, then index
#   scripts/local-repo.sh --index-only    # re-index whatever is already built
#
# boulder builds rootless, so this does not need sudo. Registering the repo with
# moss does; the command to run is printed at the end.

set -euo pipefail

repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
arch=$(uname -m)
outdir="${repo_root}/local/${arch}"

index_only=0
args=()
for arg in "$@"; do
    case "${arg}" in
        --index-only) index_only=1 ;;
        *) args+=("${arg}") ;;
    esac
done

# Map each argument to a recipe path; with no arguments, build every recipe.
recipes=()
if [[ ${#args[@]} -gt 0 ]]; then
    for arg in "${args[@]}"; do
        candidate="${repo_root}/${arg%/}"
        [[ -d "${candidate}" ]] && candidate="${candidate}/stone.yaml"
        if [[ ! -f "${candidate}" ]]; then
            echo "error: no recipe found for '${arg}'" >&2
            exit 1
        fi
        recipes+=("${candidate}")
    done
else
    while IFS= read -r recipe; do
        recipes+=("${recipe}")
    done < <(find "${repo_root}" -mindepth 3 -maxdepth 3 -name stone.yaml -not -path '*/local/*' | sort)
fi

mkdir -p "${outdir}"

if [[ ${index_only} -eq 0 ]]; then
    for recipe in "${recipes[@]}"; do
        pkgdir=$(dirname -- "${recipe}")
        echo ":: Building ${recipe#"${repo_root}"/}"
        # Build from inside the package directory rather than passing -o: that
        # way boulder refreshes the package's committed manifest.x86_64.* in
        # place, which is what keeps the recorded file list honest. Only the
        # .stone is then moved into the repository directory.
        ( cd -- "${pkgdir}" && boulder build -y stone.yaml )
        mv -- "${pkgdir}"/*.stone "${outdir}/"
    done
fi

echo ":: Indexing ${outdir}"
moss index "${outdir}"

cat <<EOF

Local repository ready: ${outdir}/stone.index

If it is not registered with moss yet, do so once:

    sudo moss repo add local file://${outdir}/stone.index -p 10

Priority 10 beats the stock repositories (priority 0), so these builds win over
the same package name from upstream. Afterwards:

    sudo moss sync

is enough to pick up anything newly built and indexed here. Note that moss only
treats a rebuild as an update if the recipe's 'release' was bumped.
EOF
