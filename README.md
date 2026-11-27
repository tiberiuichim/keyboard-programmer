# keyboard-programmer

Program the 3-key + 1-knob USB macropad (eMaj DBG05R3BM) without the vendor's
Windows software.

```
./pad status              # is it plugged in?
./pad program config/media.yaml
./pad monitor 40          # press the keys, watch it verify
```

Start with **[AGENTS.md](AGENTS.md)** — it documents the device, the mapping
file format, the hardware limitations, the raw HID protocol, and the exact
workflow to follow.

Nothing here needs the vendor software, a driver, or a daemon. `./pad udev`
(one time, needs sudo) removes the need for sudo/Docker afterwards.
