# AGENTS.md — programming the CH57x macropad in this directory

This directory is a self-contained toolkit for reprogramming a small USB
macropad. Everything an agent needs is here; read this file before touching
the device.

---

## 0. The device

| | |
|---|---|
| Product | "AJIEQ" mini mechanical keyboard, 3 keys + 1 rotary encoder |
| Vendor listing | https://www.emag.ro/mini-tastatura-mecanica-cu-3-taste-si-1-potentiometru-tastatura-mecanica-programabila-ajieqaqr-iluminare-rgb-conectare-usb-type-c-protectie-anti-static-pentru-gaming-editare-video-photoshop-cad-modela/pd/DBG05R3BM/ (SKU `DBG05R3BM`) |
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
./pad program --py FILE.yaml force the dependency-free python programmer
./pad program --rust FILE.yaml  force the upstream rust programmer
./pad bytes FILE.yaml        print the exact bytes that would be sent
./pad selftest               offline regression test (no pad, no network)
./pad doctor                 what this checkout can and cannot do offline
./pad restore                re-flash config/factory-default.yaml (stock a/b/c)
./pad monitor [SECS]         decode what the pad is actually sending (default 60)
./pad led LAYER "MODE"       set RGB, e.g. ./pad led 0 "backlight blue"
./pad build                  build the optional rust programmer
./pad udev                   install the udev rule (then no sudo/Docker needed)
```

There are **two interchangeable programmers** in this repo:

| | `tools/program.py` | `bin/ch57x-keyboard-tool` |
|---|---|---|
| Origin | written here, from the protocol in §6 | upstream `kriomant/ch57x-keyboard-tool` |
| Needs | Python 3 stdlib only | Rust toolchain to build, `libusb` to run |
| Committed? | **yes** | no (build artifact) |
| Macros | keys, modifiers, sequences, media, `<NNN>` | everything, incl. mouse actions and `{delay()}` |
| LED | not implemented | `./pad led` |
| Verified | byte-identical to upstream, see §11 | — |

`./pad program` uses the Rust one when it has been built, otherwise falls back
to the Python one automatically. **The Python one is what keeps this repo
usable if upstream disappears.**

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

The monitor labels each node it opens, because node numbers are reassigned on
every replug. The one tagged `(vendor channel)` is interface 0 — normally
silent; traffic there means something is reprogramming the pad. The other one
is interface 1, what the pad actually *does*.

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

## 7. The optional Rust programmer

`bin/ch57x-keyboard-tool` is **not committed** — it is a build artifact, and
nothing in this repo requires it. Build it with `./pad build` (Docker, ~1 minute)
if you want mouse actions, `{delay()}` or `./pad led`.

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

Full list of upstream sources and credits: [§10](#10-where-this-information-came-from).

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
  program.py                 dependency-free programmer (stdlib only)
  keytables.py               key/media name -> code tables (generated, committed)
  gen-keytables.py           regenerates keytables.py from an upstream checkout
  selftest.py                offline regression test
  capture-golden.sh          re-capture tests/golden from the Rust programmer
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
tests/golden/*.hex           expected byte streams, captured from upstream
```

Because `config/applied/`, `config/.current` and `capture/` are gitignored, a
fresh clone does not know what is on your physical pad. After cloning, run
`./pad monitor` and re-derive it, or copy those directories over by hand.

---

## 10. Where this information came from

The reverse engineering here was done by other people. This repo is a wrapper
plus field notes. Pointers, in the order they matter:

### The programmer — [`kriomant/ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool) (MIT, Rust)

Everything in §3 and §6 of this file is derived from its source.

| What | Where |
|---|---|
| Mapping-file format, full action vocabulary | [`README.md`](https://github.com/kriomant/ch57x-keyboard-tool/blob/master/README.md), [`doc/actions.md`](https://github.com/kriomant/ch57x-keyboard-tool/blob/master/doc/actions.md), [`example-mapping.yaml`](https://github.com/kriomant/ch57x-keyboard-tool/blob/master/example-mapping.yaml) |
| The byte-level protocol in §6 (driver for our `ch57x-1` model) | [`src/keyboard/k884x.rs`](https://github.com/kriomant/ch57x-keyboard-tool/blob/master/src/keyboard/k884x.rs) |
| Supported-device table, incl. `(Ch57x_1, 0x514c, 0x8851, endpoint 0x02)` | [`src/config.rs`](https://github.com/kriomant/ch57x-keyboard-tool/blob/master/src/config.rs) |
| **PR [#188](https://github.com/kriomant/ch57x-keyboard-tool/pull/188)** — added `514c:8851`, merged 2026-07-14 | *the reason we build from master, not from a tag* |
| **PR [#190](https://github.com/kriomant/ch57x-keyboard-tool/pull/190)** — added `screenbrightness*` / `webpage*` media codes | used by `config/media.yaml`; its merge commit is our pinned commit |
| PR [#169](https://github.com/kriomant/ch57x-keyboard-tool/pull/169) — earlier attempt at the same PID (closed, unmerged) | explains endpoint `0x02` vs the usual `0x04` |
| PR [#189](https://github.com/kriomant/ch57x-keyboard-tool/pull/189) — endpoint auto-detection (closed, unmerged) | context for `--endpoint-address` |
| Issue [#162](https://github.com/kriomant/ch57x-keyboard-tool/issues/162) | first report of this PID; shows the `unsupported device` panic |
| Issue [#196](https://github.com/kriomant/ch57x-keyboard-tool/issues/196) | the same panic on the same PID, using the **v1.7.0 release binary** — this is exactly the trap §7 warns about |
| Pinned build | commit [`bdbffca`](https://github.com/kriomant/ch57x-keyboard-tool/commit/bdbffca368f2084fbd111bc64463b881cd7c8fee) |

### Other tools for the same hardware (not used here, worth knowing)

* [`wimpysworld/WonKey`](https://github.com/wimpysworld/WonKey) (BlueOak-1.0.0) —
  "Macropad configuration tool for Linux". Handles CH57x **and** SayoDevice
  pads under one CLI, and additionally has vendor-firmware update and
  bootloader-recovery paths. Worth a look if you ever want to touch firmware
  rather than key maps.
* [`jvspier/macropad-rebind`](https://github.com/jvspier/macropad-rebind) (MIT) —
  same class of device, driven from a browser/WebUSB context. Its issue #9
  documents yet another pad layout variant.

### How the device was identified

Searching GitHub issues for the literal USB id `514c:8851` is what pinned this
down as a CH57x pad. **Do that first next time** — the vendor strings on these
boards are garbage (`c̪USB Keyboardȉ`), so the name on the box tells you nothing.

### Reference tables

* HID Usage Tables — <https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf>
  * Section 10 (Keyboard/Keypad) — needed for raw `"<100>"` style codes and the
    `code` byte in §6
  * Section 15 (Consumer Page) — the media usages listed in §6
    (`0x0e9` volume up, `0x0ea` volume down, `0x0e2` mute, …)

### Licensing

This repo is **MIT** (`LICENSE`, Copyright (c) 2026 Tiberiu Ichim).

Two things here are *derived from* upstream and therefore carry upstream's
notice too, and must keep it if you redistribute:

* `tools/keytables.py` — generated from upstream's Rust enums
  (Copyright 2023 Mikhail Trishchenkov, MIT; notice in the file header)
* `tests/golden/*.hex` — byte streams captured from upstream's output
  (full notice in `tests/golden/NOTICE`)

`WonKey` is BlueOak-1.0.0 and `macropad-rebind` MIT; neither is used or
redistributed here, they are only linked as alternatives.

---

## 11. Self-containment: what survives if upstream vanishes

`./pad doctor` prints this at a glance.

**Committed and dependency-free — works with no network and no upstream:**

* `tools/program.py` — Python 3 stdlib only. Parses the config, builds the §6
  byte stream, writes it to the pad's interface-0 hidraw node.
* `tools/keytables.py` — the 124 key names and 16 media names, generated from
  upstream's Rust enums and **committed**, so regenerating it does not need a
  checkout.
* `tools/monitor_hidraw.py`, `tools/capture_events.py` — stdlib only.
* `tests/golden/*.hex` — the exact byte streams the upstream Rust programmer
  sends, captured off its `RUST_LOG=trace` output.
* `AGENTS.md` §6 — the protocol itself, so the tool can be rewritten from
  scratch if both the code and the goldens are lost.

**Needs the network / upstream:**

* `./pad build` — clones `kriomant/ch57x-keyboard-tool` and pulls crates.io.
  Only needed for the Rust binary (mouse actions, `{delay()}`, `./pad led`).
* `tools/Dockerfile` / `Dockerfile.build` — Docker Hub base images. Only needed
  for the Docker fallback; if the udev rule is installed everything runs
  natively with no Docker at all.

**How the Python programmer is proven correct:**

```
python3 tools/selftest.py
```

No pad, no network. It unit-tests the YAML-subset and macro parsers, checks the
key/media tables against the HID usage tables, checks the `to_key_id` mapping
(buttons 1-based, knob 0 = 16/17/18), checks the 3×1+1knob modifier rule is
enforced on limited boards and *not* on others — and then diffs the full byte
stream for every `config/*.yaml` against `tests/golden/`.

As of writing: **72/72 packets byte-identical to the upstream Rust programmer**
for `config/media.yaml`, and the resulting pad behaviour was verified on
hardware with `./pad monitor`.

Regenerate goldens (this programs the pad): `./tools/capture-golden.sh`.
If upstream ever changes the protocol, the selftest fails loudly rather than
silently writing garbage.

---

## 12. Android / car head units

The pad stores its map in its own flash, so **Android needs no app, driver or
settings** — program it on a PC, plug it into the tablet, done. Layer switching
is the hardware side button.

`config/android.yaml` is a layout built from only the bindings Android honours.

### What the pad looks like to Android

Interface 1 advertises four collections: `1` 6-key keyboard, `2` mouse,
`4` 9-key NKRO, `5` 16-bit Consumer page. Interface 0 (vendor usage page
`0xFF00`) is simply ignored. All four are standard, and Android binds them.

### Binding compatibility

| Binding | Android | Notes |
|---|---|---|
| `prev` `play` `next` | ✅ | Consumer `0x0b6/0x0cd/0x0b5` → `KEYCODE_MEDIA_PREVIOUS/PLAY_PAUSE/NEXT`. Framework-level: works in any media app, even with the screen off. |
| `volumeup` `volumedown` | ✅ | `0x0e9/0x0ea` → `KEYCODE_VOLUME_UP/DOWN`, consumed by the framework before any app sees it. |
| `mute` | ⚠️ usually | `0x0e2` → `KEYCODE_VOLUME_MUTE`. Mapped on most builds, not all. |
| `calculator` | ✅ | `KEYCODE_CALCULATOR`, Android 4.4+. |
| `escape` | ✅ | Android treats ESC as **BACK** — the single most useful key here. |
| `enter` `tab` `space` `backspace`, letters, digits, arrows | ✅ | standard HID keyboard. |
| `ctrl-x` style combos | ✅ | |
| `click` `wheel` `move` (mouse macros) | ✅ | but Android draws an on-screen pointer. |
| `webpageback` `webpageforward` | ⚠️ | only honoured inside a browser/WebView. |
| **`alt-tab`** | ❌ | no window-switcher shortcut exists. |
| `screenlock` | ❌ | no user-space keycode; screen off needs a device-admin app. |
| `screenbrightnessup/down` | ❌ | Android routes brightness through the system and ignores the HID usages. |

### Android 13 and 14 specifically

Android ≤12 reads HID through the kernel input layer (evdev) — mature, and
consumer keys are reliably mapped. **Android 13+ may use the "HID raw" path**,
where the framework parses the reports itself; consumer-control handling there
is less battle-tested. So if media keys are dead on a 13/14 tablet, suspect the
host's HID path, not the pad — the same pad on a Linux box will look perfect.

### Other gotchas

* **Power.** The descriptor claims 400 mA. Tablets often cap VBUS on OTG.
  Flaky or repeated reconnects → powered hub or a Y-cable.
* **Composite devices.** A few builds bind only the first HID interface.
  Symptom: a mouse cursor appears but no keys work.
* **OTG enable.** Some tablets need host mode switched on manually.
* **The mouse collection exists whether you use it or not** — the pad always
  advertises it, which is why some builds park a pointer on screen.

### Verifying on the tablet (no guessing)

```
adb shell dumpsys input                       # is the pad enumerated at all?
adb shell getevent -li                        # list devices and their keymaps
adb shell getevent -l                         # then press a key: shows the keycode
```

If `getevent` shows `KEY_PLAYPAUSE` / `KEY_VOLUMEDOWN` but the app ignores it,
the pad is fine and the app is the problem. If `getevent` shows nothing, it is
the HID path or power.
