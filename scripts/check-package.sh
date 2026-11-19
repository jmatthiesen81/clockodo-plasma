#!/usr/bin/env bash
# SPDX-License-Identifier: MPL-2.0
# Check a built package (run as root inside the Arch container):
# metadata, file list, namcap, test install and a daemon smoke test.
#   scripts/check-package.sh dist/clockodo-plasma-0.1.0-1-any.pkg.tar.zst
#
# Without arguments on the host it builds the package and runs the check in
# the container (scripts/build-package.sh --check).
set -euo pipefail

if [ $# -eq 0 ]; then
    exec "$(dirname "$0")/build-package.sh" --check
fi

pkg=$1
id=io.github.jmatthiesen81.clockodoplasma

echo "== metadata"
pacman -Qip "$pkg"

echo "== files"
files=$(pacman -Qlpq "$pkg")
echo "$files"
for required in \
    /usr/bin/clockodo-plasma-daemon \
    /usr/lib/clockodo-plasma/clockodo_plasma/main.py \
    /usr/lib/systemd/user/clockodo-plasma.service \
    /usr/share/dbus-1/services/io.github.jmatthiesen81.ClockodoPlasma.service \
    "/usr/share/plasma/plasmoids/$id/metadata.json" \
    "/usr/share/plasma/plasmoids/$id/contents/ui/main.qml" \
    "/usr/share/plasma/plasmoids/$id/contents/ui/translations.js" \
    "/usr/share/plasma/plasmoids/$id/contents/config/config.qml"; do
    grep -qx "$required" <<<"$files" || { echo "missing: $required" >&2; exit 1; }
done
if grep -q 'site-packages' <<<"$files"; then
    echo "package must not install into site-packages" >&2
    exit 1
fi

echo "== namcap"
namcap "$pkg" || true

echo "== install"
pacman -U --noconfirm "$pkg"

echo "== daemon"
version=$(clockodo-plasma-daemon --version)
echo "$version"
expected=$(pacman -Qip "$pkg" | sed -nE 's/^Version +: ([^-]+)-.*/\1/p')
[ "$version" = "clockodo-plasma-daemon $expected" ] || { echo "version mismatch" >&2; exit 1; }

# Smoke test on a private session bus: the daemon must come up via D-Bus
# activation and answer GetState (no Secret Service here -> secret_locked).
runuser -u builder -- dbus-run-session -- python3 - <<'EOF'
import asyncio, json
from dbus_fast import Message, MessageType
from dbus_fast.aio import MessageBus

async def main():
    bus = await MessageBus().connect()
    for _ in range(50):
        reply = await bus.call(Message(
            destination="io.github.jmatthiesen81.ClockodoPlasma",
            path="/io/github/jmatthiesen81/ClockodoPlasma",
            interface="io.github.jmatthiesen81.ClockodoPlasma",
            member="GetState"))
        if reply.message_type == MessageType.METHOD_RETURN:
            state = json.loads(reply.body[0])
            print("daemon state:", state["status"])
            assert state["status"] in ("secret_locked", "unconfigured"), state
            return
        await asyncio.sleep(0.2)
    raise SystemExit(f"daemon did not answer: {reply.body}")

asyncio.run(main())
EOF

echo "== qmllint"
qmllint=/usr/lib/qt6/bin/qmllint
if [ -x "$qmllint" ]; then
    # Unresolved imports of Plasma modules only produce warnings; syntax errors fail.
    "$qmllint" --max-warnings -1 "/usr/share/plasma/plasmoids/$id/contents/ui/"*.qml \
        "/usr/share/plasma/plasmoids/$id/contents/config/"*.qml || {
        echo "qmllint found errors" >&2; exit 1; }
fi

echo "== remove"
pacman -R --noconfirm clockodo-plasma
echo "package check passed"
