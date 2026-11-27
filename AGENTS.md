# AGENTS.md — programming the CH57x macropad in this directory

This directory is a self-contained toolkit for reprogramming a small USB
macropad. Everything an agent needs is here; read this file before touching
the device.

---

## 0. The device

| | |
|---|---|
| Product | "AJIEQ" mini mechanical keyboard, 3 keys + 1 rotary encoder (eMaj listing DBG05R3BM) |
| Real identity | generic **WCH CH57x "SayoDevice"-family** macropad, not a real keyboard |
| USB ID | **`514c:8851`** (vendor string is garbage: `c̪USB Keyboardȉ`) |
| Speed | Full Speed (12 Mbit). If `speed` reads 1.5, the cable is charge-only. |
| Serial | unique per unit; deliberately not recorded here. Read it live with `./pad status`. |
| MCU firmware | vendor CH57x blob. **Not flashable / no read-back of the key map.** |
| Programming model | the pad stores key maps in its own flash; you write them over HID and the tool exits. There is **no daemon and no driver**. |

### USB topology (2 interfaces)

* **Interface 0** — vendor channel. Interrupt **IN `0x82`** + **OUT `0x02`**, 64-byte
  packets, HID Report ID **3**. *This is the programming endpoint.*
  Note the OUT endpoint is `0x02`, **not** `0x04` like most sibling boards.
* **Interface 1** — boot keyboard. Interrupt IN `0x81`, 16-byte packets.
  Report IDs: `1` = 6-key keyboard, `2` = mouse (buttons/X/Y/wheel),
  `4` = 9-key NKRO, `5` = 16-bit Consumer page (media keys).

The pad emulates **keyboard + mouse + consumer-control** devices. That is why
you can bind mouse clicks and wheel ticks to keys.

---

## 1. The one tool you need

```
./pad <command>
```

```
./pad status                 is the pad plugged in, and can we touch it?
./pad keys                   every key / modifier / media name you may use
./pad validate FILE.yaml     check a mapping file without touching the device
./pad program FILE.yaml      validate + flash + record as the active mapping
./pad restore                re-flash config/factory-default.yaml (stock a/b/c)
./pad monitor [SECS]         decode what the pad is actually sending (default 60)
./pad led LAYER "MODE"       set RGB, e.g. ./pad led 0 "backlight blue"
./pad build                  rebuild the programmer from the pinned commit
./pad udev                   install the udev rule (then no sudo/Docker needed)
```

`./pad` auto-selects the transport: it runs the binary natively if
`/dev/bus/usb/...` is writable, otherwise it falls back to a `--privileged`
Docker container (image `kbpad`, built on demand from `tools/Dockerfile`).
Right now on this machine it uses **Docker**, because the udev rule is not
installed. Run `./pad udev` once (needs sudo) to make everything native.

---

## 2. Standard operating procedure

Follow this every time. Do not skip step 4.

1. `./pad status` — confirm the device is present and note the ACCESS line.
2. Ask the user what each key and each knob action should do. Do not guess.
3. Write a YAML in `config/` (copy `config/media.yaml` as a starting point),
   then `./pad validate config/<name>.yaml`.
4. `./pad program config/<name>.yaml`
5. **`./pad monitor 40` and have the user physically press every key and both
   knob directions.** Compare the decoded output against the YAML. A flash can
   report success and still be wrong if the wrong `model:`/geometry was used.
6. Tell the user which layer they are on and how to change layers.

### ⚠️ There is no read-back

The device will not give you its current mapping. Consequences:

* You **cannot** back up a mapping you did not write.
* `./pad program` copies the flashed YAML into `config/applied/` and records
  the path in `config/.current`. **That file is the only record of device
  state.** Read `config/.current` before assuming you know what is on the pad.
* Warn the user before overwriting a mapping you never recorded.

`config/factory-default.yaml` holds the stock mapping, recovered by hand from
observed output (keys → `a b c`, knob → `1 / 2 / 3`). Layers 2 and 3 of the
factory mapping were never observed and are unknown.

---

## 3. Mapping file format

```yaml
model: ch57x-1        # REQUIRED. For 514c:8851 it is always ch57x-1.
orientation: normal   # normal | upsidedown | clockwise | counterclockwise
rows: 1               # counted in NORMAL orientation
columns: 3
knobs: 1
layers:
  - buttons:
      - ["prev", "play", "next"]
    knobs:
      - ccw: volumedown
        press: mute
        cw: volumeup
```

* `buttons` is a grid of `rows` × `columns` **in normal orientation** (keys on
  the left, knob on the right). For this pad that is one row of three.
  Use `orientation:` to rotate the map instead of rearranging it in your head.
* `null` means "don't touch this binding" — it does **not** clear it.
* Exactly **3 layers** exist in hardware. Switch them with the small **side
  button** on the pad's flank; the LED flashes 1/2/3 briefly.
* `./pad keys` prints every accepted key name. Unlisted keys work via raw HID
  usage in angle brackets, e.g. `"<100>"`.
* Media keys (`play`, `next`, `volumeup`, `mute`, `screenbrightnessup`,
  `webpageback`, `calculator`, `screenlock`, …) **cannot be mixed with
  modifiers** inside one macro.

### Hardware limitations of the 3×1 + 1-knob board

* Modifiers are honoured **only on the first key of a sequence**.
  `ctrl-c` ✅, `ctrl-c,alt-v` ❌ (the tool rejects this at `validate`).
* `rows: 1` (or `columns: 1`) together with `knobs: 1` is what triggers that
  restriction — do not "fix" it by changing the geometry, the tool would then
  emit bindings the hardware ignores.
* Max 18 steps per macro sequence. Max delay 6000 ms.

---

## 4. Reading the pad back (verification)

`./pad monitor` runs `tools/monitor_hidraw.py`, which reads the pad's
`/dev/hidraw*` nodes directly and decodes raw HID reports — no evdev layer, no
guessing. It prints lines like:

```
[/dev/hidraw9] CONSUMER VOLUME_UP (0x0e9)
[/dev/hidraw9] KEYBOARD LCTRL C
[/dev/hidraw9] MOUSE LEFT wheel=+1
[/dev/hidraw9] NKRO LSHIFT A
```

`hidraw9` = interface 1 (what the pad *does*), `hidraw8` = interface 0 (the
vendor channel; it is normally silent — traffic there means something is
reprogramming the pad).

`tools/capture_events.py` is the evdev-level equivalent; prefer the hidraw one.

---

## 5. RGB backlight

```
./pad led <0|1|2> "<mode> <color>"
```

```
./pad led 0 "backlight blue"
./pad led 1 "press green"
./pad led 2 off
```

Layer is **0-based** (0, 1, 2). Modes for this model: `off`, `backlight`,
`press`, `shock`, `shock2`. Colors: `red orange yellow green cyan blue purple`;
`backlight` additionally takes `white`.

**Syntax is verified, hardware effect is not.** LED commands are model-specific
and upstream warns they vary between boards. Dry-run the syntax without
touching the device using the hidden `test-led` subcommand:

```
./bin/ch57x-keyboard-tool test-led --model ch57x-1 0 "backlight blue"
# -> Generated 128 bytes of data      (parse OK, nothing sent)
```

Then apply one and watch the pad before doing the rest. There is no way to
read or restore the previous LED state.

---

## 6. The raw protocol (if you must go without the tool)

Everything is 64-byte interrupt-OUT packets on **interface 0, endpoint `0x02`**,
first byte `0x03` (HID Report ID 3). `tools/dump_usb.py` re-dumps descriptors.

```
open device, then send 64 x 0x00                      # init

03 fe <key_id> <layer+1> <kind> 00 00 00 00 00 <n> <mods,code> x n   # bind
03 fe <key_id> <layer+1> 05 <delay_lo> <delay_hi>     # inter-key delay
03 aa aa 00 ...                                       # end of binding
03 fd fe ff                                           # commit programming
03 aa aa 00 ...

03 fe b0 <layer+1> 08 00 00 00 00 00 01 00 <led_code> # LED, then commit
```

* `kind`: `1` keyboard, `2` media, `3` mouse
* `key_id`: **buttons are 1-based** → button *n* = `n+1` (so 1,2,3 here).
  Knob *n* (0-based): `16 + 3*n + action`, action `0`=ccw, `1`=press, `2`=cw
  → knob 0 = 16, 17, 18.
* `mods` is a bitmask of LCTRL LSHIFT LALT LWIN RCTRL RSHIFT RALT RWIN;
  `code` is a HID keyboard usage ID.
* Media: payload is `[00, usage_lo, usage_hi, ...]`, usage on the Consumer page
  (0x0e9 volume up, 0x0ea volume down, 0x0e2 mute, 0x0cd play, 0x0b5 next,
  0x0b6 prev).
* `led_code = (color << 4) | mode`, mode `0`=off `1`=backlight `2`=shock
  `3`=shock2 `4`=press `5`=backlight-white; color `0`=white `1`=red … `7`=purple.

Each message is padded to 64 bytes and sent as its own packet.

---

## 7. The programmer binary

`bin/ch57x-keyboard-tool` is **not committed** — it is a build artifact. Create
it once with `./pad build` (needs Docker, ~1 minute); `./pad status` tells you
if it is missing.

It is [`kriomant/ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool)
(MIT, Rust), built from a **pinned master commit**, see `tools/build-tool.sh`:

```
COMMIT=bdbffca368f2084fbd111bc64463b881cd7c8fee
```

**Do not "just download the latest release".** The newest tag, v1.7.0
(Jan 2026), does **not** know `514c:8851` and panics with
`internal error: entered unreachable code: unsupported device`. Support
landed in master on 2026-07-14 (PR #188), and PR #190 added the
`screenbrightness*` / `webpage*` media codes used by `config/media.yaml`.

Rebuild with `./pad build` (needs Docker; ~1 minute). The build writes into
`build/src/ch57x`, which is disposable and git-ignored.

Upstream issue worth knowing: <https://github.com/kriomant/ch57x-keyboard-tool/issues/196>
reports the crash on this PID for people using the tagged release.

---

## 8. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `DEVICE: NOT PRESENT` in `./pad status` | Charge-only USB-C cable, or the pad is on a hub that dropped it. Try another cable/port. |
| `unsupported device` panic | You are running a v1.7.0 release binary. `./pad build` from the pinned commit. |
| `Access denied (insufficient permissions)` | Run `./pad udev` once, replug, or let Docker handle it. Check `./pad status` ACCESS line. |
| Flash succeeds, keys do nothing | Wrong `model:` or wrong `rows`/`columns`/`knobs`. Must be `ch57x-1`, `1`×`3`, `1`. |
| Keys map to the wrong physical key | Use `orientation:` rather than reordering the grid. |
| Modifiers silently ignored | The 3×1+1knob limitation, see §3. |
| hidraw node numbers changed | They are reassigned on every replug. `./pad` re-derives them; never hardcode `hidraw8`. |
| Need to know what is on the pad | `cat config/.current`, then `./pad monitor`. |

---

## 9. File map

Everything below is committed except entries marked *(local, gitignored)*.

```
pad                          entry point — always use this
AGENTS.md                    this file
README.md
bin/ch57x-keyboard-tool      pinned upstream programmer   (local, gitignored)
config/
  media.yaml                 example layout, the one currently flashed
  factory-default.yaml       hand-recovered stock mapping = the only "backup"
  applied/                   every flash ever done, timestamped (local, gitignored)
  .current                   path of the last flashed file    (local, gitignored)
tools/
  monitor_hidraw.py          decode raw HID reports off the pad  (./pad monitor)
  capture_events.py          evdev-level equivalent
  dump_usb.py                dump USB/HID descriptors from scratch
  build-tool.sh              rebuild the binary at the pinned commit
  install-udev.sh            one-time permission setup, no more sudo/Docker
  99-macropad.rules          the udev rule
  Dockerfile                 runtime image `kbpad`
  Dockerfile.build           rust build image `kbbuild`
build/src/ch57x              upstream checkout used for building (local, gitignored)
capture/                     saved monitor/capture logs       (local, gitignored)
```

Because `config/applied/`, `config/.current` and `capture/` are gitignored, a
fresh clone does not know what is on your physical pad. After cloning, run
`./pad monitor` and re-derive it, or copy those directories over by hand.
