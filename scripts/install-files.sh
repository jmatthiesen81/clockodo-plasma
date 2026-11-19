#!/usr/bin/env bash
# SPDX-License-Identifier: MPL-2.0
# Single source of truth for the installed files.
# Used by the development PKGBUILD and by the release recipe of the pacman
# repository build project.
#
#   scripts/install-files.sh DESTDIR [PREFIX]
set -euo pipefail

destdir=${1:?usage: install-files.sh DESTDIR [PREFIX]}
prefix=${2:-/usr}
root=$(cd "$(dirname "$0")/.." && pwd)

plasmoid_id=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["KPlugin"]["Id"])' \
    "$root/plasmoid/metadata.json")
libdir="$prefix/lib/clockodo-plasma"

# Python code (no site-packages, see packaging/clockodo-plasma-daemon).
install -d "$destdir$libdir/clockodo_plasma"
install -m644 "$root"/backend/clockodo_plasma/*.py "$destdir$libdir/clockodo_plasma/"
python3 -m compileall -q -d "$libdir" "$destdir$libdir" >/dev/null

# Start script.
install -d "$destdir$prefix/bin"
sed "s|@LIBDIR@|$libdir|" "$root/packaging/clockodo-plasma-daemon" \
    >"$destdir$prefix/bin/clockodo-plasma-daemon"
chmod 755 "$destdir$prefix/bin/clockodo-plasma-daemon"

# systemd user unit and D-Bus activation.
install -Dm644 "$root/packaging/clockodo-plasma.service" \
    "$destdir$prefix/lib/systemd/user/clockodo-plasma.service"
install -Dm644 "$root/packaging/io.github.jmatthiesen81.ClockodoPlasma.service" \
    "$destdir$prefix/share/dbus-1/services/io.github.jmatthiesen81.ClockodoPlasma.service"

# Plasmoid.
target="$destdir$prefix/share/plasma/plasmoids/$plasmoid_id"
install -d "$target/contents/ui"
install -m644 "$root/plasmoid/metadata.json" "$target/metadata.json"
# translations.js holds the widget's translations (language chosen in the settings).
install -m644 "$root"/plasmoid/contents/ui/*.qml "$root"/plasmoid/contents/ui/*.js \
    "$target/contents/ui/"

# Documentation and license.
install -Dm644 "$root/README.md" "$destdir$prefix/share/doc/clockodo-plasma/README.md"
if [ -f "$root/LICENSE" ]; then
    install -Dm644 "$root/LICENSE" "$destdir$prefix/share/licenses/clockodo-plasma/LICENSE"
fi
