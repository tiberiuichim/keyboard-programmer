# keyboard-programmer

Program the 3-key + 1-knob USB macropad without the vendor's Windows software.

The pad sold as ["AJIEQ" mini mechanical keyboard, 3 keys + 1 potentiometer](https://www.emag.ro/mini-tastatura-mecanica-cu-3-taste-si-1-potentiometru-tastatura-mecanica-programabila-ajieqaqr-iluminare-rgb-conectare-usb-type-c-protectie-anti-static-pentru-gaming-editare-video-photoshop-cad-modela/pd/DBG05R3BM/)
(SKU `DBG05R3BM`) is really a generic **WCH CH57x "SayoDevice"-family**
macropad, USB id `514c:8851`. It is reprogrammed by writing 64-byte vendor HID
reports to interface 0, endpoint `0x02`. No vendor software, no driver, no
daemon.

```bash
./pad status                  # is it plugged in?
./pad program config/media.yaml
./pad monitor 40              # press the keys, watch it verify
./pad selftest                # offline regression test, no pad needed
./pad doctor                  # what this checkout can do without network
```

There are two interchangeable programmers: `tools/program.py` (Python 3 stdlib
only, committed, no upstream needed) and the upstream Rust binary built by
`./pad build` (optional; needed only for mouse actions, `{delay()}` and RGB).
`./pad program` picks automatically. The Python one is byte-identical to
upstream and is what keeps this repo working if upstream disappears.

Start with **[AGENTS.md](AGENTS.md)** — device reference, mapping-file format,
hardware limitations, the raw byte-level protocol, and the workflow to follow.

### Layouts in `config/`

| File | For |
|---|---|
| `media.yaml` | desktop media/volume |
| `android.yaml` | Android 13/14 tablet or car head unit — only bindings Android honours, volume on the knob in every layer |
| `factory-default.yaml` | the stock `a b c` / `1 2 3` mapping, i.e. the only backup there is |

See AGENTS.md §12 for what works on Android and what silently does nothing
(`alt-tab`, `screenlock`, `screenbrightness*`).

Run `./pad udev` once (needs sudo) to stop needing sudo/Docker afterwards.

## Credits

This repo is a wrapper plus field notes. The reverse engineering is other
people's work — see [AGENTS.md §10](AGENTS.md#10-where-this-information-came-from)
for the full list.

* [`kriomant/ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool)
  (MIT) — the programmer this wraps. Build from **master**, not from the
  `v1.7.0` tag: support for `514c:8851` landed in
  [PR #188](https://github.com/kriomant/ch57x-keyboard-tool/pull/188) and is in
  no release yet.
* [`wimpysworld/WonKey`](https://github.com/wimpysworld/WonKey) (BlueOak-1.0.0)
  and [`jvspier/macropad-rebind`](https://github.com/jvspier/macropad-rebind)
  (MIT) — alternative tools for the same hardware family.

## License

MIT — see [LICENSE](LICENSE).

`tools/keytables.py` and `tests/golden/*.hex` are derived from
[`kriomant/ch57x-keyboard-tool`](https://github.com/kriomant/ch57x-keyboard-tool)
(Copyright 2023 Mikhail Trishchenkov, MIT); upstream's notice is kept in the
file header and in [`tests/golden/NOTICE`](tests/golden/NOTICE).
