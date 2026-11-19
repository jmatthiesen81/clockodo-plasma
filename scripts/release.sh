#!/usr/bin/env sh
# SPDX-License-Identifier: MPL-2.0
# Prepare a release: set the version, update CHANGELOG.md, commit and create the tag.
#   scripts/release.sh 1.2.0            # release
#   scripts/release.sh 1.2.0-rc.1       # pre-release: CHANGELOG stays, files get 1.2.0
#   scripts/release.sh 1.2.0 --dry-run  # show what would happen
#
# The version (without a pre-release suffix, pacman's pkgver allows no "-") is
# written to backend/clockodo_plasma/__init__.py, plasmoid/metadata.json and
# packaging/arch/PKGBUILD. For a release the section "## [Unreleased]" becomes
# "## [1.2.0] - <today>", a new empty "## [Unreleased]" is added above it and
# the compare links at the end are updated. If CHANGELOG.md already has a
# section for the version (prepared by hand), it is used as it is. Nothing is
# pushed; the script prints the push commands. Pushing the tag starts the
# release workflow.
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
CHANGELOG=$ROOT/CHANGELOG.md
SECTION=$ROOT/scripts/changelog-section.sh
VERSION_FILES="backend/clockodo_plasma/__init__.py plasmoid/metadata.json packaging/arch/PKGBUILD"

die() { echo "release: $*" >&2; exit 1; }

VERSION=""
DRY=false
for arg in "$@"; do
    case $arg in
        --dry-run|-n) DRY=true ;;
        -h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        -*) die "unknown option $arg" ;;
        *) [ -z "$VERSION" ] || die "more than one version given"; VERSION=$arg ;;
    esac
done
[ -n "$VERSION" ] || die "usage: scripts/release.sh <version> [--dry-run]"

# same tag patterns as .github/workflows/release.yml, no "v" prefix
echo "$VERSION" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$' \
    || die "\"$VERSION\" is not a version like 1.2.0 or 1.2.0-rc.1 (no \"v\" prefix)"
case $VERSION in *-*) PRE=true ;; *) PRE=false ;; esac
BASE=${VERSION%%-*}

cd "$ROOT"
git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository"
[ -z "$(git status --porcelain)" ] || die "the working tree has uncommitted changes; commit or stash them first"
! git rev-parse -q --verify "refs/tags/$VERSION" >/dev/null || die "tag $VERSION already exists"

# Releases are tags on the trunk branch "canon". A maintenance branch named
# after the release line (e.g. "0.1", created from a tag only when an old line
# needs a fix) may release versions of that line.
TRUNK=canon
BRANCH=$(git rev-parse --abbrev-ref HEAD)
MINOR=$(echo "$VERSION" | sed -E 's/^([0-9]+\.[0-9]+).*/\1/')
if [ "$BRANCH" != "$TRUNK" ] && [ "$BRANCH" != "$MINOR" ]; then
    echo "release: note: releasing $VERSION from branch $BRANCH, not from $TRUNK" >&2
fi

has_section() { grep -Eq "^## \[$(echo "$1" | sed 's/[.]/\\./g')\]" "$CHANGELOG"; }

# ---- version in the source files ----

set_versions() {
    sed -i -E "s/^__version__ = \"[^\"]*\"/__version__ = \"$BASE\"/" backend/clockodo_plasma/__init__.py
    sed -i -E "s/(\"Version\": )\"[^\"]*\"/\1\"$BASE\"/" plasmoid/metadata.json
    sed -i -E "s/^pkgver=[^ ]*/pkgver=$BASE/; s/^pkgrel=.*/pkgrel=1/" packaging/arch/PKGBUILD
}

if $DRY; then
    echo "Would set version $BASE in: $VERSION_FILES"
else
    set_versions
    git diff --quiet -- $VERSION_FILES || echo "Version $BASE set in: $VERSION_FILES"
fi

# ---- CHANGELOG.md ----

if $PRE; then
    echo "Pre-release: CHANGELOG.md stays as it is; the release notes come from the section of"
    echo "$VERSION, $BASE or [Unreleased]:"
elif has_section "$VERSION"; then
    echo "CHANGELOG.md already has a section for $VERSION; using it as it is:"
else
    has_section Unreleased || die "CHANGELOG.md has neither a section [$VERSION] nor [Unreleased]"
    "$SECTION" Unreleased "$CHANGELOG" >/dev/null 2>&1 \
        || die "the section [Unreleased] in CHANGELOG.md is empty; add the changes of $VERSION first"

    DATE=$(date +%Y-%m-%d)
    # repository URL and previous version from the existing links / headings
    URL=$(grep -Eo '^\[[^]]+\]: https://github\.com/[^/]+/[^/]+/' "$CHANGELOG" | head -n 1 | sed -E 's/^\[[^]]+\]: //; s#/$##')
    [ -n "$URL" ] || die "no GitHub link at the end of CHANGELOG.md to take the repository URL from"
    # empty for the first release: then the version links to its release page
    PREV=$(grep -E '^## \[[0-9]' "$CHANGELOG" | head -n 1 | sed -E 's/^## \[([^]]+)\].*/\1/')

    TMP=$(mktemp)
    awk -v version="$VERSION" -v date="$DATE" -v url="$URL" -v prev="$PREV" '
        function links() {
            print "[Unreleased]: " url "/compare/" version "...HEAD"
            if (prev == "") print "[" version "]: " url "/releases/tag/" version
            else print "[" version "]: " url "/compare/" prev "..." version
            done_links = 1
        }
        /^## \[Unreleased\]/ && !done_heading {
            print "## [Unreleased]"; print ""
            print "## [" version "] - " date
            done_heading = 1; next
        }
        /^\[Unreleased\]: / { links(); next }
        # no [Unreleased] link yet: put both links before the first version link
        /^\[[0-9][^]]*\]: / && !done_links { links() }
        { print }
    ' "$CHANGELOG" > "$TMP"

    if $DRY; then
        echo "Would update CHANGELOG.md:"
        diff -u "$CHANGELOG" "$TMP" | sed -n '3,$p' || true
        rm -f "$TMP"
    else
        cat "$TMP" > "$CHANGELOG"
        rm -f "$TMP"
    fi
    echo "Release notes of $VERSION:"
fi

if $DRY && ! $PRE && ! has_section "$VERSION"; then
    # the file was not changed: show the notes from the [Unreleased] section
    "$SECTION" Unreleased "$CHANGELOG" | sed 's/^/  | /'
else
    "$SECTION" "$VERSION" "$CHANGELOG" | sed 's/^/  | /' \
        || die "no release notes for $VERSION in CHANGELOG.md"
fi

# ---- commit and tag ----

if $DRY; then
    echo
    echo "Would commit:  chore(release): $VERSION (if files changed)"
    echo "Would tag:     $VERSION (annotated) on $BRANCH"
    exit 0
fi

CHANGED=false
# shellcheck disable=SC2086 # the file list is meant to be split
if ! git diff --quiet -- CHANGELOG.md $VERSION_FILES; then
    git add CHANGELOG.md $VERSION_FILES
    git commit -q -m "chore(release): $VERSION"
    CHANGED=true
    echo
    echo "Committed:  chore(release): $VERSION"
fi
git tag -a "$VERSION" -m "Clockodo Plasma $VERSION"
echo "Tagged:     $VERSION"
echo
echo "Push to start the release workflow:"
echo "  git push origin $BRANCH"
echo "  git push origin $VERSION"
echo
echo "Undo before pushing:"
echo "  git tag -d $VERSION"
if $CHANGED; then echo "  git reset --hard HEAD~1"; fi
