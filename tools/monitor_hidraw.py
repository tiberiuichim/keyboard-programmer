#!/usr/bin/env python3
"""Decode raw HID reports straight off the pad's hidraw nodes.

Node numbers are reassigned on every replug, so they are discovered at
runtime from sysfs: the node whose parent USB interface is ':1.0' is the vendor
channel; the other carries the keyboard/mouse/consumer reports.
"""
import os, sys, glob, time, select, struct

HID_KEY = {
    0x04: "A", 0x05: "B", 0x06: "C", 0x07: "D", 0x08: "E", 0x09: "F", 0x0a: "G",
    0x0b: "H", 0x0c: "I", 0x0d: "J", 0x0e: "K", 0x0f: "L", 0x10: "M", 0x11: "N",
    0x12: "O", 0x13: "P", 0x14: "Q", 0x15: "R", 0x16: "S", 0x17: "T", 0x18: "U",
    0x19: "V", 0x1a: "W", 0x1b: "X", 0x1c: "Y", 0x1d: "Z",
    0x1e: "1", 0x1f: "2", 0x20: "3", 0x21: "4", 0x22: "5", 0x23: "6", 0x24: "7",
    0x25: "8", 0x26: "9", 0x27: "0",
    0x28: "ENTER", 0x29: "ESC", 0x2a: "BACKSPACE", 0x2b: "TAB", 0x2c: "SPACE",
    0x2d: "MINUS", 0x2e: "EQUAL", 0x2f: "[", 0x30: "]", 0x31: "\\", 0x32: "#",
    0x33: ";", 0x34: "'", 0x35: "`", 0x36: ",", 0x37: ".", 0x38: "/",
    0x39: "CAPSLOCK", 0x3a: "F1", 0x3b: "F2", 0x3c: "F3", 0x3d: "F4", 0x3e: "F5",
    0x3f: "F6", 0x40: "F7", 0x41: "F8", 0x42: "F9", 0x43: "F10", 0x44: "F11",
    0x45: "F12", 0x4a: "INSERT", 0x4b: "HOME", 0x4c: "PAGEUP", 0x4d: "DELETE",
    0x4e: "END", 0x4f: "PAGEDOWN", 0x50: "RIGHT", 0x51: "LEFT", 0x52: "DOWN",
    0x53: "UP",
}
MODS = ["LCTRL", "LSHIFT", "LALT", "LWIN", "RCTRL", "RSHIFT", "RALT", "RWIN"]
CONSUMER = {
    0x00e9: "VOLUME_UP", 0x00ea: "VOLUME_DOWN", 0x00e2: "MUTE", 0x00cd: "PLAY",
    0x00b5: "NEXT", 0x00b6: "PREV", 0x00b7: "STOP", 0x00e4: "PLAY_PAUSE",
    0x006f: "BRIGHT_UP", 0x0070: "BRIGHT_DOWN", 0x0192: "CALCULATOR",
    0x019e: "SCREEN_LOCK", 0x0182: "FAVORITES", 0x0223: "HOME_URL",
    0x0224: "BACK_URL", 0x0225: "FWD_URL",
}


def decode(rid, d):
    if rid == 1:                       # 6-key boot protocol
        mods = [MODS[i] for i in range(8) if d[0] >> i & 1]
        keys = [HID_KEY.get(k, "0x%02x" % k) for k in d[2:8] if k]
        return "KEYBOARD " + " ".join(mods + keys) if (mods or keys) else "KEYBOARD (clear)"
    if rid == 4:                       # 9-key NKRO
        mods = [MODS[i] for i in range(8) if d[0] >> i & 1]
        keys = []
        for byte_i, byte in enumerate(d[2:11]):
            for bit in range(8):
                if byte >> bit & 1:
                    u = byte_i * 8 + bit + 1
                    keys.append(HID_KEY.get(u, "0x%02x" % u))
        return "NKRO " + " ".join(mods + keys) if (mods or keys) else "NKRO (clear)"
    if rid == 2:                       # mouse
        btn = ["LEFT", "RIGHT", "MIDDLE"]
        b = [btn[i] for i in range(3) if d[0] >> i & 1]
        x, y, w = (struct.pack("b", v).decode("latin1") for v in d[1:4])
        x, y, w = [v if v >= 0 else v - 256 for v in (d[1], d[2], d[3])]
        parts = b + (["x=%+d" % x] if x else []) + (["y=%+d" % y] if y else []) \
            + (["wheel=%+d" % w] if w else [])
        return "MOUSE " + " ".join(parts) if parts else "MOUSE (clear)"
    if rid == 5:                       # consumer / media
        v = d[0] | (d[1] << 8)
        return "CONSUMER %s (0x%03x)" % (CONSUMER.get(v, "?"), v) if v else "CONSUMER (clear)"
    return "REPORT id=%d %s" % (rid, d.hex())


def main():
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    nodes = []
    for h in sorted(glob.glob("/dev/hidraw*")):
        sysfs = "/sys/class/hidraw/%s" % os.path.basename(h)
        try:
            ue = open("%s/device/uevent" % sysfs).read()
        except OSError:
            continue
        if "514C" not in ue or "8851" not in ue:
            continue
        # interface 0 is the vendor/programming channel. The node number itself
        # is reassigned on every replug, so never key off it.
        try:
            iface = os.path.basename(os.path.realpath("%s/device/.." % sysfs))
        except OSError:
            iface = ""
        try:
            nodes.append((os.open(h, os.O_RDONLY), h, iface.endswith(":1.0")))
        except OSError:
            print("cannot open", h)
    for _, h, vendor in nodes:
        print("watching %s (%s)" % (h, "vendor channel" if vendor else "reports"))
    print("\n>> Press the 3 keys, rotate the knob both ways, press the knob,")
    print(">> and press the side layer button. Listening %ds...\n" % dur)

    end = time.time() + dur
    while time.time() < end:
        r, _, _ = select.select([f for f, _, _ in nodes], [], [], 0.2)
        for fd in r:
            try:
                pkt = os.read(fd, 128)
            except OSError:
                continue
            src, vendor = next((p, v) for f, p, v in nodes if f == fd)
            if not pkt:
                continue
            rid, body = pkt[0], pkt[1:]
            if vendor:
                if body.strip(b"\x00"):
                    print("  [vendor] %s" % body[:16].hex())
                continue
            print("  [%s] %s" % (src, decode(rid, body)))
    print("\ndone")
main()
