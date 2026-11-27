#!/usr/bin/env python3
"""Dump every descriptor of the macro pad over raw USB (libusb)."""
import sys
import usb.core

VID, PID = 0x514C, 0x8851

def hexdump(b, base=0):
    out = []
    for i in range(0, len(b), 16):
        chunk = b[i:i + 16]
        hexs = " ".join("%02x" % x for x in chunk)
        asc = "".join(chr(x) if 32 <= x < 127 else "." for x in chunk)
        out.append("%04x  %-48s |%s|" % (base + i, hexs, asc))
    return "\n".join(out)

def get_desc(dev, dtype, index, length, windex=0):
    return bytes(dev.ctrl_transfer(0x80, 0x06, (dtype << 8) | index, windex, length))

dev = usb.core.find(idVendor=VID, idProduct=PID)
if dev is None:
    print("device not found")
    sys.exit(1)

print("=== DEVICE DESCRIPTOR ===")
dd = get_desc(dev, 1, 0, 18)
print(hexdump(dd))
extra = get_desc(dev, 1, 0, 64)
if len(extra) > 18:
    print("--- bytes beyond 18 ---")
    print(hexdump(extra, 18))

print("\n=== CONFIGURATION DESCRIPTOR (full) ===")
cfg = get_desc(dev, 2, 0, 9)
total = cfg[2] | (cfg[3] << 8)
cfg = get_desc(dev, 2, 0, total)
print(hexdump(cfg))

print("\n=== STRING DESCRIPTORS ===")
try:
    langs = list(get_desc(dev, 3, 0, 255)[2:])
    langs = [langs[i] | (langs[i + 1] << 8) for i in range(0, len(langs) - 1, 2)]
except Exception as e:
    print("langIDs failed:", e)
    langs = [0x0409]
print("LANGIDs:", ["%04x" % l for l in langs])

def decode_utf16(raw):
    s = raw.decode("utf-16-le", "replace")
    return s

for i in range(0, 6):
    for l in langs:
        try:
            raw = get_desc(dev, 3, i, 255, l)
            n = raw[0]
            print("  idx %d lang %04x: len=%d  utf16=%r  ascii=%r"
                  % (i, l, n, decode_utf16(raw[2:n]), raw[2:n]))
            break
        except Exception as e:
            print("  idx %d lang %04x: ERR %s" % (i, l, e))

print("\n=== HID REPORT DESCRIPTORS ===")
i, rd = 0, []
while i < len(cfg):
    bl, bt = cfg[i], cfg[i + 1]
    if not bl:
        break
    if bt == 4:
        print("\n-- interface %d: class=%d subclass=%d protocol=%d neps=%d"
              % (cfg[i + 2], cfg[i + 4], cfg[i + 5], cfg[i + 6], cfg[i + 3]))
    if bt == 0x21:
        rdlen = cfg[i + 7] | (cfg[i + 8] << 8)
        print("   HID: bcdHID=%04x country=%d rdlen=%d"
              % (cfg[i + 4] | (cfg[i + 5] << 8), cfg[i + 6], rdlen))
        try:
            r = bytes(dev.ctrl_transfer(0x81, 0x06, 0x2200, cfg[i + 2], rdlen))
            print("   report descriptor (%d bytes):" % len(r))
            print(hexdump(r))
            rd.append((cfg[i + 2], r))
        except Exception as e:
            print("   read failed:", e)
    if bt == 5:
        print("   EP addr=%02x attr=%d maxpkt=%d interval=%d"
              % (cfg[i + 2], cfg[i + 3],
                 (cfg[i + 4] | (cfg[i + 5] << 8)) & 0x7ff, cfg[i + 6]))
    i += bl

for ifc, r in rd:
    open("/work/report_if%d.bin" % ifc, "wb").write(r)
print("\nsaved %d report descriptor(s)" % len(rd))
