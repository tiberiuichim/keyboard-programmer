#!/usr/bin/env python3
"""Record what the macro pad currently sends (keycodes, mouse, consumer).

Pure-stdlib evdev reader (no pip deps). Run inside a privileged container
with /dev/input mounted.
"""
import os, sys, glob, time, select, struct

FMT = "llHHI"
SZ = struct.calcsize(FMT)

KEY = {
    1: "ESC", 2: "1", 3: "2", 4: "3", 5: "4", 6: "5", 7: "6", 8: "7", 9: "8",
    10: "9", 11: "0", 12: "MINUS", 13: "EQUAL", 14: "BACKSPACE", 15: "TAB",
    16: "Q", 17: "W", 18: "E", 19: "R", 20: "T", 21: "Y", 22: "U", 23: "I",
    24: "O", 25: "P", 26: "LEFTBRACE", 27: "RIGHTBRACE", 28: "ENTER",
    29: "LCTRL", 30: "A", 31: "S", 32: "D", 33: "F", 34: "G", 35: "H", 36: "J",
    37: "K", 38: "L", 39: "SEMICOLON", 40: "APOSTROPHE", 41: "GRAVE",
    42: "LSHIFT", 43: "BACKSLASH", 44: "Z", 45: "X", 46: "C", 47: "V", 48: "B",
    49: "N", 50: "M", 51: "COMMA", 52: "DOT", 53: "SLASH", 54: "RSHIFT",
    55: "KPASTERISK", 56: "LALT", 57: "SPACE", 58: "CAPSLOCK",
    59: "F1", 60: "F2", 61: "F3", 62: "F4", 63: "F5", 64: "F6", 65: "F7",
    66: "F8", 67: "F9", 68: "F10", 87: "F11", 88: "F12",
    96: "KPENTER", 97: "RCTRL", 100: "RALT", 102: "HOME", 103: "UP",
    104: "PAGEUP", 105: "LEFT", 106: "RIGHT", 107: "END", 108: "DOWN",
    109: "PAGEDOWN", 110: "INSERT", 111: "DELETE",
    113: "MUTE", 114: "VOLUMEUP", 115: "VOLUMEDOWN",
    125: "LWIN/CMD", 126: "RWIN/CMD", 127: "COMPOSE",
    148: "CALCULATOR", 162: "PREVIOUSSONG", 163: "NEXTSONG",
    164: "PLAYPAUSE", 165: "STOPCD", 204: "PLAYPAUSE2",
    224: "BRIGHTNESSDOWN", 225: "BRIGHTNESSUP",
}
BTN = {272: "LEFT", 273: "RIGHT", 274: "MIDDLE", 275: "SIDE", 276: "EXTRA"}
REL = {0: "X", 1: "Y", 6: "WHEEL", 8: "WHEEL_HI_RES"}


def describe(t, c, v):
    if t == 1:
        n = KEY.get(c) or ("BTN_" + BTN[c] if c in BTN else "code=%d" % c)
        return "%s%s" % (n, "" if v == 1 else ("(up)" if v == 0 else "(repeat)"))
    if t == 2:
        return "%s %+d" % (REL.get(c, c), v)
    if t == 4:
        return "MSCAN %d" % v
    return "type=%d code=%d val=%d" % (t, c, v)


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else "Keyboard"
    dur = int(sys.argv[2]) if len(sys.argv) > 2 else 90
    fds = []
    for p in sorted(glob.glob("/dev/input/event*")):
        try:
            nm = open("/sys/class/input/%s/device/name" % os.path.basename(p)).read().strip()
        except OSError:
            continue
        if want.lower() not in nm.lower() or "razer" in nm.lower():
            continue
        try:
            fds.append((os.open(p, os.O_RDONLY), p, nm))
        except OSError:
            pass
    if not fds:
        print("no matching input devices found")
        sys.exit(1)
    for _, p, nm in fds:
        print("listening on %s  [%s]" % (p, nm))
    print("\n>> Press EVERY key, rotate the knob both ways, press the knob,")
    print(">> and press the side/layer switch. Listening %ds...\n" % dur)

    end, cur = time.time() + dur, []
    while time.time() < end:
        r, _, _ = select.select([f for f, _, _ in fds], [], [], 0.2)
        for fd in r:
            try:
                data = os.read(fd, SZ * 128)
            except OSError:
                continue
            for i in range(0, len(data) - SZ + 1, SZ):
                _, _, t, c, v = struct.unpack(FMT, data[i:i + SZ])
                if t == 0:
                    if cur:
                        print("  -> " + " + ".join(cur))
                        cur = []
                    continue
                cur.append(describe(t, c, v))
    print("\ndone")


main()
