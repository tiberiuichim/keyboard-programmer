#!/usr/bin/env python3
"""Offline regression test for tools/program.py. No pad, no network needed.

    python3 tools/selftest.py

Two layers:
  1. unit tests of the YAML-subset and macro parsers
  2. golden comparison: the byte stream program.py produces for every
     config/*.yaml must equal tests/golden/<name>.hex, which was captured
     from the upstream Rust programmer (RUST_LOG=trace, 'send:' lines) and
     verified to make the physical pad behave correctly.

Regenerate goldens (needs the pad plugged in):
    ./tools/capture-golden.sh
"""
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import program as P                                    # noqa: E402
from keytables import KEYCODES, MEDIACODES             # noqa: E402

fails = []


def check(name, got, want):
    if got != want:
        fails.append("%s\n     got: %r\n    want: %r" % (name, got, want))


# ------------------------------------------------------------- 1. parsers
print("parser unit tests")

check("yaml: scalars",
      P.parse_yaml_subset("model: ch57x-1\nrows: 1\nknobs: 1\n"),
      {"model": "ch57x-1", "rows": "1", "knobs": "1"})

check("yaml: null and comments",
      P.parse_yaml_subset("a: null  # nothing\nb: ~\nc:\n"),
      {"a": None, "b": None, "c": None})

check("yaml: flow sequence",
      P.parse_yaml_subset('buttons:\n  - ["prev", "play", "next"]\n'),
      {"buttons": [["prev", "play", "next"]]})

check("yaml: nested knob map",
      P.parse_yaml_subset("knobs:\n  - ccw: volumedown\n    press: mute\n    cw: volumeup\n"),
      {"knobs": [{"ccw": "volumedown", "press": "mute", "cw": "volumeup"}]})

check("yaml: quoted scalar containing #",
      P.parse_yaml_subset('a: "# not a comment"\n'),
      {"a": "# not a comment"})

check("yaml: real config parses",
      [(len(l[0]), len(l[1])) for l in
       P.load_config(os.path.join(ROOT, "config", "media.yaml"))[3]],
      [(3, 1), (3, 1), (3, 1)])

check("macro: plain key", P.parse_macro("a"), ("keys", [(0, 0x04)]))
check("macro: combo", P.parse_macro("ctrl-c"), ("keys", [(1, 0x06)]))
check("macro: two modifiers",
      P.parse_macro("ctrl-alt-delete"), ("keys", [(1 | 4, 0x4c)]))
check("macro: sequence",
      P.parse_macro("a,b"), ("keys", [(0, 0x04), (0, 0x05)]))
check("macro: media", P.parse_macro("volumeup"), ("media", 0x0E9))
check("macro: raw usage", P.parse_macro("<100>"), ("keys", [(0, 100)]))
check("macro: modifier only", P.parse_macro("shift"), ("keys", [(2, None)]))
check("macro: alias opt==alt", P.parse_macro("opt-tab"), ("keys", [(4, 0x2b)]))
check("macro: null", P.parse_macro(None), None)

for bad, why in [("play,next,a", "media mixed with keys"),
                 ("notakey", "unknown key"),
                 ("click", "mouse action"),
                 ("{delay(100)}a", "delay option")]:
    try:
        P.parse_macro(bad)
        fails.append("macro %r (%s): should have been rejected" % (bad, why))
    except P.MacroError:
        pass

# key table sanity against the HID usage tables
for n, want in [("a", 0x04), ("z", 0x1D), ("1", 0x1E), ("0", 0x27),
                ("enter", 0x28), ("escape", 0x29), ("f1", 0x3A),
                ("f13", 0x68), ("pageup", 0x4B), ("nonushash", 0x32)]:
    check("keytable: %s" % n, KEYCODES[n], want)
for n, want in [("volumeup", 0x0E9), ("volumedown", 0x0EA), ("mute", 0x0E2),
                ("play", 0x0CD), ("prev", 0x0B6), ("screenlock", 0x19E)]:
    check("mediatable: %s" % n, MEDIACODES[n], want)

# key id mapping (upstream to_key_id)
check("key_id: button 0", P.key_id_button(0), 1)
check("key_id: button 2", P.key_id_button(2), 3)
check("key_id: knob0 ccw", P.key_id_knob(0, 0), 16)
check("key_id: knob0 cw", P.key_id_knob(0, 2), 18)

# the 3x1+1knob modifier restriction must be enforced
try:
    P.build(1, 3, 1, [([None, "ctrl-c,alt-v", None], [])])
    fails.append("modifier restriction: 'ctrl-c,alt-v' should be rejected on 3x1+1knob")
except P.MacroError:
    pass
P.build(1, 3, 1, [([None, "ctrl-c", None], [])])       # must NOT raise
P.build(3, 4, 2, [(["ctrl-c,alt-v"] * 12, [])])        # must NOT raise: not limited

# ------------------------------------------------------------- 2. goldens
print("golden byte streams")

golden_dir = os.path.join(ROOT, "tests", "golden")
if not os.path.isdir(golden_dir):
    fails.append("no tests/golden directory - run ./tools/capture-golden.sh")
else:
    for cfg in sorted(glob.glob(os.path.join(ROOT, "config", "*.yaml"))):
        name = os.path.basename(cfg)[:-5]
        gpath = os.path.join(golden_dir, name + ".hex")
        if not os.path.exists(gpath):
            fails.append("missing golden for config/%s.yaml" % name)
            continue
        want = [l.strip() for l in open(gpath) if l.strip()]
        out = subprocess.run([sys.executable, os.path.join(HERE, "program.py"),
                              cfg, "--dump"], capture_output=True, text=True)
        if out.returncode != 0:
            fails.append("program.py failed on %s: %s" % (name, out.stderr.strip()))
            continue
        got = [m.group(1).replace(" ", "")
               for m in (re.match(r"\s*\d+\s+((?:[0-9a-f]{2} ?){63}[0-9a-f]{2})", l)
                         for l in out.stdout.splitlines()) if m]
        if got != want:
            first = next((i for i, (a, b) in enumerate(zip(got, want)) if a != b), None)
            fails.append("config/%s.yaml differs from golden (%d vs %d packets, first diff at %s)"
                         % (name, len(got), len(want), first))
        else:
            print("  config/%s.yaml == golden (%d packets)" % (name, len(got)))

print()
if fails:
    print("FAILED (%d):" % len(fails))
    for f in fails:
        print("  - " + f)
    sys.exit(1)
print("all selftests passed")
