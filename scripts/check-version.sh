#!/usr/bin/env sh
# SPDX-License-Identifier: MPL-2.0
# Check that all version numbers agree (and match a tag, if given):
#   scripts/check-version.sh            # files agree with each other
#   scripts/check-version.sh 1.2.0-rc.1 # files carry 1.2.0
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

py=$(sed -nE 's/^__version__ = "([^"]+)"/\1/p' backend/clockodo_plasma/__init__.py)
meta=$(python3 -c 'import json; print(json.load(open("plasmoid/metadata.json"))["KPlugin"]["Version"])')
pkg=$(sed -nE 's/^pkgver=([^ ]+).*/\1/p' packaging/arch/PKGBUILD)

echo "__init__.py: $py  metadata.json: $meta  PKGBUILD: $pkg"
[ "$py" = "$meta" ] && [ "$py" = "$pkg" ] || { echo "version numbers differ" >&2; exit 1; }

if [ $# -gt 0 ]; then
    base=${1%%-*}
    [ "$py" = "$base" ] || { echo "tag $1 does not match version $py" >&2; exit 1; }
fi
