#!/usr/bin/env bash
# Rebuild bin/ch57x-keyboard-tool from a pinned upstream commit, inside Docker.
#
# Why a pinned commit and not the latest release:
#   The newest *tagged* release (v1.7.0, Jan 2026) does NOT know about our
#   USB id 514c:8851. Support landed in master on 2026-07-14 (PR #188).
#   PR #190 added the screenbrightness*/webpage* media codes we use.
#   So we build from master, pinned below.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"

# PINNED UPSTREAM COMMIT — change only deliberately.
COMMIT="bdbffca368f2084fbd111bc64463b881cd7c8fee"
REPO="https://github.com/kriomant/ch57x-keyboard-tool"

SRC="$ROOT/build/src"
mkdir -p "$SRC"

echo "Building runtime image (kbpad)..."
docker build -t kbpad -q -f "$HERE/Dockerfile" "$HERE" >/dev/null

echo "Building toolchain image (kbbuild)..."
docker build -t kbbuild -q -f "$HERE/Dockerfile.build" "$HERE" >/dev/null

echo "Fetching $COMMIT ..."
docker run --rm -v "$SRC:/src" kbbuild sh -eu -c "
    if [ -d /src/ch57x/.git ]; then
        git -C /src/ch57x fetch --depth 1 origin $COMMIT
        git -C /src/ch57x checkout -q FETCH_HEAD
    else
        git clone $REPO /src/ch57x
        git -C /src/ch57x fetch --depth 1 origin $COMMIT
        git -C /src/ch57x checkout -q FETCH_HEAD
    fi
    git -C /src/ch57x log -1 --format='checked out %H %s'
    cd /src/ch57x && cargo build --release
"

# The build runs as root inside the container; hand the binary back to the user.
docker run --rm -v "$ROOT/bin:/out" -v "$SRC/ch57x/target/release/ch57x-keyboard-tool:/in" \
    alpine sh -c "cp /in /out/ch57x-keyboard-tool && chown $(id -u):$(id -g) /out/ch57x-keyboard-tool"

echo
echo "OK -> $ROOT/bin/ch57x-keyboard-tool"
"$ROOT/bin/ch57x-keyboard-tool" --version || true
