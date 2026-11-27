#!/usr/bin/env bash
# Capture the exact byte stream the upstream Rust programmer sends, and store it
# as tests/golden/<name>.hex for tools/selftest.py to diff against.
#
#   ./tools/capture-golden.sh [config/foo.yaml ...]
#
# WARNING: this actually programs the pad, once per config file. The pad must be
# plugged in. It leaves the pad running the LAST config in the list.
#
# How it works: with RUST_LOG=trace the tool logs every message twice - once in
# send_message() while building the buffer, once in send_to_device() when it
# hits the wire - plus one extra init packet logged only by send_to_device.
# So the log is: init, N messages, N messages. We keep init + the second half.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(dirname "$HERE")"
BIN="$ROOT/bin/ch57x-keyboard-tool"
OUTDIR="$ROOT/tests/golden"

[[ -x "$BIN" ]] || { echo "missing $BIN - run ./pad build"; exit 1; }

configs=("$@")
if [[ ${#configs[@]} -eq 0 ]]; then
    mapfile -t configs < <(ls "$ROOT"/config/*.yaml)
fi

mkdir -p "$OUTDIR"

for cfg in "${configs[@]}"; do
    cfg="$(readlink -f "$cfg")"
    name="$(basename "$cfg" .yaml)"
    echo "capturing $name ..."

    raw="$(docker run --rm --privileged -e RUST_LOG=trace \
              -v /dev/bus/usb:/dev/bus/usb \
              -v "$BIN:/opt/tool:ro" -v "$(dirname "$cfg"):/cfg:ro" \
              kbpad /opt/tool upload "/cfg/$(basename "$cfg")" 2>&1 \
              | grep -o 'send: \[.*\]' | sed 's/send: \[//; s/\]$//; s/ //g; s/,//g')"

    printf '%s\n' "$raw" | python3 -c '
import sys
lines = [l.strip() for l in sys.stdin if l.strip()]
if len(lines) < 3 or (len(lines) - 1) % 2:
    sys.exit("unexpected log shape: %d send: lines" % len(lines))
init, rest = lines[0], lines[1:]
n = len(rest) // 2
sent = [init] + rest[n:]
if rest[:n] != rest[n:]:
    sys.exit("send_message and send_to_device logs differ - unexpected upstream change")
out = "%s/%s.hex" % (sys.argv[1], sys.argv[2])
open(out, "w").write("\n".join(sent) + "\n")
print("  %d packets -> %s" % (len(sent), out))
' "$OUTDIR" "$name"
done

echo
echo "now run: python3 tools/selftest.py"
