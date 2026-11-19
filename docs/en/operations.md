# Operations

Running, observing and updating the daemon, and building, releasing and publishing the package.

## Daemon

```bash
systemctl --user status clockodo-plasma
systemctl --user restart clockodo-plasma
journalctl --user -u clockodo-plasma -f
```

- The daemon logs to stderr, which systemd writes to the journal. Headers, request and response bodies, customer names and descriptions are never logged; registered secrets are replaced by `***` as a second safeguard.
- For verbose logs, run it by hand after stopping the unit: `systemctl --user stop clockodo-plasma && clockodo-plasma-daemon --debug`.
- `clockodo-plasma-daemon --version` prints the installed version.
- Only one daemon can own the bus name; a second instance exits with code 1.

Inspect the state on the bus:

```bash
busctl --user call io.github.jmatthiesen81.ClockodoPlasma /io/github/jmatthiesen81/ClockodoPlasma \
    io.github.jmatthiesen81.ClockodoPlasma GetState
```

## Build and check the package

```bash
scripts/build-package.sh          # build only → dist/clockodo-plasma-<version>-<rel>-any.pkg.tar.zst
scripts/build-package.sh --check  # build and check
```

[build-package.sh](../../scripts/build-package.sh) builds the image from [Dockerfile.arch](../../Dockerfile.arch), mounts the checkout read-only, copies it for the unprivileged user `builder` and runs `makepkg` with the development [PKGBUILD](../../packaging/arch/PKGBUILD). Containers run with `--rm`. [check-package.sh](../../scripts/check-package.sh) then checks, as root inside the container:

1. package metadata and required files, and that nothing goes to `site-packages`,
2. `namcap` (warnings only),
3. test installation with `pacman -U`,
4. `clockodo-plasma-daemon --version` matches the package version,
5. D-Bus activation on a private session bus answers `GetState` (expected `secret_locked`, because the container has no Secret Service),
6. `qmllint` on the installed QML (errors fail; warnings about unqualified access to `root` are expected),
7. removal with `pacman -R`.

[install-files.sh](../../scripts/install-files.sh) is the only place that knows the installed layout; the development PKGBUILD and the release recipe of the pacman repository both call it.

## Release

Releases follow Semantic Versioning; tags have no `v` prefix. Changes are collected under `## [Unreleased]` in [CHANGELOG.md](../../CHANGELOG.md).

```bash
scripts/release.sh 0.1.0 --dry-run   # preview
scripts/release.sh 0.1.0             # set versions, date the changelog, commit, tag
git push origin <branch>
git push origin 0.1.0
```

[release.sh](../../scripts/release.sh):

- writes the version to `backend/clockodo_plasma/__init__.py`, `plasmoid/metadata.json` and `packaging/arch/PKGBUILD` (and resets `pkgrel` to 1),
- turns `[Unreleased]` into `## [X.Y.Z] - <date>`, adds a new empty `[Unreleased]` and updates the compare links (the first release links to its release page),
- commits `chore(release): X.Y.Z` and creates an annotated tag; nothing is pushed.

A pre-release `X.Y.Z-rc.N` sets the base version `X.Y.Z` in the files (pacman's `pkgver` allows no `-`) and leaves the changelog unchanged.

Pushing the tag runs [release.yml](../../.github/workflows/release.yml): version and changelog check, tests, package check, then a GitHub release "Clockodo Plasma X.Y.Z" with `clockodo-plasma-X.Y.Z.tar.gz` (from `git archive`) and `SHA256SUMS`. The release notes are the changelog section ([changelog-section.sh](../../scripts/changelog-section.sh)) followed by GitHub's generated notes. Tags with a suffix become pre-releases.

## Release checklist

Before a release is published to the pacman repository, check on a CachyOS machine with Plasma ≥ 6.4 and a real Clockodo account:

- [ ] Installation with pacman from the own repository works; package and repository signatures are verified.
- [ ] The widget appears; play/pause and today's total are always visible; stale data is recognisable.
- [ ] A click opens the popup and syncs at once.
- [ ] Start, stop and switch work; the booking context is visible before the start.
- [ ] A clock started on another device is never stopped silently; changes from other devices are detected.
- [ ] Double clicks and lost answers cause no duplicate or wrong bookings; network errors book nothing.
- [ ] Today's total matches Clockodo, also after a restart and later corrections; day change, DST and a different Clockodo time zone are handled.
- [ ] The API key is in KWallet and in no log; a locked wallet and a rejected key are explained clearly.
- [ ] The reminder on screen lock works; suspend/resume triggers a sync.
- [ ] Interval and language can be changed.
- [ ] A package update keeps settings and widget position; a Python minor update of Arch does not break the package.
- [ ] Uninstalling removes the program files and names the remaining user data.

The automated parts (unit and D-Bus tests, package build as non-root, content and dependency checks, release tarball with `SHA256SUMS`) run in CI.

## Publishing to the pacman repository

GitHub releases contain **no binary package**. The installable package is built by the separate repository build project (`cachyos-repository`) from the release tarball and signed there. Reasons:

- makepkg builds are not byte-identical (build date, `PACKAGER`, `.BUILDINFO`). Two packages with the same file name but different content (one from GitHub, one from the repository) would collide in the pacman cache, and `pacman -Syu` would fail on the checksum or signature.
- The repository's signing key also signs every other package in it and must never go to GitHub; it stays on the signing machine.
- A second pacman repository with the same package name would win or lose depending on the order in `pacman.conf`.

Steps in `cachyos-repository`:

1. `scripts/update-recipe.sh --check` finds the new GitHub release.
2. `scripts/update-recipe.sh clockodo-plasma` sets `pkgver`, `pkgrel=1` and `sha256sums` and compares them with `SHA256SUMS` of the release.
3. `scripts/build.sh clockodo-plasma` (verification runs automatically), then `scripts/publish.sh clockodo-plasma`.
4. On the signing machine: `scripts/sign-repo.sh` with `SIGN_REMOTE` pointing to the build server.
5. Sync to the web server in two passes (packages first, then the database with `--delete`).
6. Smoke test on CachyOS: `sudo pacman -Syu clockodo-plasma`.

Pre-releases are not published to the pacman repository (its retention sorts with `sort --version-sort`, not `vercmp`).

### Missing in `cachyos-repository`

- `recipes/clockodo-plasma/PKGBUILD`: source = release tarball `clockodo-plasma-X.Y.Z.tar.gz`, `sha256sums`, `package()` calls `scripts/install-files.sh "$pkgdir" /usr`; dependencies as in [packaging/arch/PKGBUILD](../../packaging/arch/PKGBUILD).
- `recipes/clockodo-plasma/verify.sh`: otherwise verification calls every `/usr/bin/*` with `--version` and expects the package version; an own script should also check plasmoid metadata, unit and D-Bus service file and start the daemon under `dbus-run-session`.
- `scripts/update-recipe.sh`: add `clockodo-plasma` to `APPS`, get the latest version from the GitHub releases API (like Joplin), read the checksum from `SHA256SUMS`; a token header while the GitHub repository is private.
- Pin the base image in `build.conf` by digest.

### Web server

The pacman repository is served by a Debian server with Plesk; Plesk's nginx runs as a reverse proxy in front of Apache. The repository lives in the web space of a subscription, and the files belong to its system user.

- Run rsync as the **subscription's system user** (check that its SSH shell provides rsync). Otherwise the owners change, Plesk can no longer manage the files and the symlinks are not served.
- Symlinks `<repo>.db` / `<repo>.files`: nginx (with "Smart static files processing") applies `disable_symlinks if_not_owner`, Apache applies `SymLinksIfOwnerMatch`. Symlink and target must belong to the same user, which holds when rsync runs as the subscription user (assumption based on Plesk's defaults; verify on the server).
- Basic auth, if wanted, through Plesk's "Password-protected directories".
- `Cache-Control: no-cache` for database and signatures and blocking of dotfiles as additional nginx directives (or Apache directives if Apache serves the files).

[Index](index.md) · [Deutsch](../de/operations.md)
