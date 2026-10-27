#!/usr/bin/env python3
"""A Max for Live device described for a language model (or anything else that wants to drive it): what the device
is, and for each parameter what it does, its range and unit, where it starts, and where it sits on Push.

    python3 tools/m4l-tools/describe.py Device.amxd              the description, as JSON
    python3 tools/m4l-tools/describe.py Device.amxd -o out.json  into a file
    python3 tools/m4l-tools/describe.py --schema                 the JSON Schema it follows (schema.json)

Everything comes from the device file itself: the parameters Live sees, the Info View text the device's builder
wrote for each control (its annotation), the device's own Info text, and its Push pages. A device with no Info View
text still gets its ranges, units and pages; the "about" fields are then empty. SCHEMA.md explains each field.
Standard library only.
"""

import json
import sys
from pathlib import Path

from amxd import boxes, device_kind, read_device

FORMAT, VERSION = "m4l-device-description", "0.1"
SCHEMA = Path(__file__).resolve().parent / "schema.json"

# Live's parameter_unitstyle: what a value means
UNITS = {0: None, 1: None, 2: "ms", 3: "Hz", 4: "dB", 5: "%", 6: "pan", 7: "semitones", 8: "MIDI note", 9: "custom",
         10: None}
TYPES = {0: "continuous", 1: "integer", 2: "choice"}
SHOWN = {0: "automatable", 1: "stored", 2: "hidden"}     # parameter_invisible: 1 saved, not automated; 2 neither
LIVE_DEFAULT_MAX = 127                                   # Live's range when a device saves none


def _valueof(box):
    return box.get("saved_attribute_attributes", {}).get("valueof", {})


def parameter(box):
    v = _valueof(box)
    kind = TYPES.get(v.get("parameter_type", 0), "other")
    options = v.get("parameter_enum") or []
    lo = v.get("parameter_mmin", 0)
    hi = v.get("parameter_mmax", len(options) - 1 if options else LIVE_DEFAULT_MAX)
    initial = (v.get("parameter_initial") or [lo])[0] if v.get("parameter_initial_enable", 1) else None
    unit = UNITS.get(v.get("parameter_unitstyle", 1))
    p = {"name": v.get("parameter_longname") or box.get("varname", ""),
         "short_name": v.get("parameter_shortname") or v.get("parameter_longname") or "",
         "about": box.get("annotation") or None,
         "type": kind,
         "visibility": SHOWN.get(v.get("parameter_invisible", 0), "automatable")}
    if kind == "choice":
        p["options"] = list(options)
        p["default"] = options[int(initial)] if initial is not None and 0 <= int(initial) < len(options) else None
    else:
        p["range"] = [lo, hi]
        p["unit"] = unit
        if unit == "custom":
            p["unit_format"] = v.get("parameter_units", "")
        if v.get("parameter_exponent", 1) != 1:
            p["curve"] = v["parameter_exponent"]
        p["default"] = initial
    return p


def describe(path):
    patcher, _ = read_device(path)
    params = [parameter(b) for b in boxes(patcher) if b.get("parameter_enable")]
    pages = []
    banks = patcher.get("parameters", {}).get("parameterbanks", {})
    for _, bank in sorted(banks.items(), key=lambda kv: int(kv[0])):
        names = [n if n and n != "-" else None for n in bank.get("parameters", [])]
        pages.append({"name": bank.get("name", ""), "parameters": names})
    where = {n: (pg["name"], i + 1) for pg in pages for i, n in enumerate(pg["parameters"]) if n}
    for p in params:
        page = where.get(p["name"])
        p["push"] = {"page": page[0], "slot": page[1]} if page else None
    return {"format": FORMAT, "version": VERSION,
            "device": {"name": Path(path).stem, "kind": device_kind(path),
                       "about": patcher.get("description") or None},
            "parameters": params,
            "push_pages": pages}


def main(argv):
    if "--schema" in argv:
        print(SCHEMA.read_text(), end="")
        return 0
    args = [a for a in argv if not a.startswith("-")]
    if not args:
        print(__doc__)
        return 2
    out = json.dumps(describe(args[0]), indent=1, ensure_ascii=False) + "\n"
    if "-o" in argv:
        Path(argv[argv.index("-o") + 1]).write_text(out)
    else:
        print(out, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
