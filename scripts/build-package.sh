#!/usr/bin/env bash
# SPDX-License-Identifier: MPL-2.0
# Build the Arch package from this checkout in the Arch container.
# Result: dist/clockodo-plasma-<version>-<rel>-any.pkg.tar.zst
#   scripts/build-package.sh            # build only
#   scripts/build-package.sh --check    # build, then scripts/check-package.sh inside
set -euo pipefail

root=$(cd "$(dirname "$0")/.." && pwd)
runtime=${CONTAINER_RUNTIME:-docker}
image=${CLOCKODO_IMAGE:-clockodo-plasma-arch:latest}
check=false
[ "${1:-}" = "--check" ] && check=true

"$runtime" build -q -t "$image" -f "$root/Dockerfile.arch" "$root" >/dev/null
mkdir -p "$root/dist"

# The checkout is mounted read-only and copied for the unprivileged builder.
"$runtime" run --rm \
    -v "$root:/src:ro" \
    -v "$root/dist:/dist" \
    -e CHECK="$check" \
    -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
    "$image" bash -euo pipefail -c '
        cp -a /src /home/builder/src
        rm -rf /home/builder/src/.venv /home/builder/src/dist
        chown -R builder: /home/builder/src
        cd /home/builder/src/packaging/arch
        runuser -u builder -- env PKGDEST=/home/builder/out \
            CLOCKODO_PLASMA_SRC=/home/builder/src makepkg --clean --cleanbuild --force --nodeps
        pkg=$(ls /home/builder/out/*.pkg.tar.zst)
        if [ "$CHECK" = true ]; then
            /home/builder/src/scripts/check-package.sh "$pkg"
        fi
        install -m644 -o "$HOST_UID" -g "$HOST_GID" "$pkg" /dist/
        echo "built: dist/$(basename "$pkg")"
    '
