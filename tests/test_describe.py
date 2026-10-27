#!/usr/bin/env python3
"""Device descriptions (tools/m4l-tools/describe.py): a made-up device's, field by field; every device here valid by
the schema, and what two of them say checked against the devices."""

import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "m4l-tools" if (ROOT / "tools" / "m4l-tools").is_dir() else ROOT    # here, or on its own
sys.path.insert(0, str(TOOLS))
import describe  # noqa: E402
from amxd import read_device  # noqa: E402

failures = []


def expect(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


try:
    import jsonschema
except ImportError:
    jsonschema = None
schema = json.loads((TOOLS / "schema.json").read_text())


def dial(name, short, about, **v):
    return {"box": {"id": name, "maxclass": "live.dial", "parameter_enable": 1, "annotation": about,
                    "saved_attribute_attributes": {"valueof": dict(parameter_longname=name, parameter_shortname=short,
                                                                   **v)}}}


print("a made-up device")
PATCH = {"description": "A test delay.",
         "boxes": [dial("Time", "Time", "How long the echo waits", parameter_mmin=1, parameter_mmax=2000,
                        parameter_unitstyle=2, parameter_exponent=3, parameter_initial=[250]),
                   dial("Mode", "Mode", "Tape or digital", parameter_type=2, parameter_enum=["Tape", "Digital"],
                        parameter_initial=[1]),
                   {"box": {"id": "p", "maxclass": "newobj", "text": "p inner", "patcher": {"boxes": [
                       dial("Hidden", "Hid", None, parameter_invisible=2)]}}}],
         "parameters": {"parameterbanks": {"0": {"index": 0, "name": "Delay", "parameters": ["Mode", "-", "Time"]}}}}
with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "Test Delay.amxd"
    body = json.dumps({"patcher": PATCH}).encode() + b"\x00"
    path.write_bytes(b"ampf" + struct.pack("<I", 4) + b"aaaa" + b"meta" + struct.pack("<II", 4, 0) + b"ptch"
                     + struct.pack("<I", len(body)) + body)
    d = describe.describe(path)
time, mode, hidden = d["parameters"]
expect(d["device"] == {"name": "Test Delay", "kind": "audio_effect", "about": "A test delay."}
       and time == {"name": "Time", "short_name": "Time", "about": "How long the echo waits", "type": "continuous",
                    "visibility": "automatable", "range": [1, 2000], "unit": "ms", "curve": 3, "default": 250,
                    "push": {"page": "Delay", "slot": 3}}
       and mode["options"] == ["Tape", "Digital"] and mode["default"] == "Digital" and mode["push"]["slot"] == 1
       and hidden["visibility"] == "hidden" and hidden["push"] is None and hidden["about"] is None
       and d["push_pages"] == [{"name": "Delay", "parameters": ["Mode", None, "Time"]}],
       "its Info text; a knob's range in ms on a curve, where it starts, its Push slot; a choice by name; a hidden "
       "parameter in a subpatcher, on no page" + ("" if time.get("unit") == "ms" else f": {d}"))
expect(jsonschema is None or not list(jsonschema.Draft202012Validator(schema).iter_errors(d)),
       "valid by schema.json" + ("" if jsonschema else " (jsonschema not installed: not checked)"))

paths = sorted((ROOT / "devices").rglob("*.amxd"))
if paths:
    print("every device here, by the schema")
    bad, odd = [], []
    for p in paths:
        d = describe.describe(p)
        if jsonschema:
            try:
                jsonschema.validate(d, schema)
            except jsonschema.ValidationError as e:
                bad.append(f"{p.name}: {e.message[:80]}")
        names = {q["name"] for q in d["parameters"]}
        on_pages = {n for pg in d["push_pages"] for n in pg["parameters"] if n}
        n = sum(1 for b in describe.boxes(read_device(p)[0]) if b.get("parameter_enable"))
        if not on_pages <= names or len(d["parameters"]) != n:
            odd.append(p.name)
    expect(jsonschema is not None and not bad, f"the {len(paths)} devices' descriptions are valid by schema.json"
           + (f": {bad[:3]}" if bad else "" if jsonschema else " (jsonschema not installed)"))
    expect(not odd, "each lists every parameter Live sees, and its Push pages name only those"
           + (f": {odd[:3]}" if odd else ""))

    print("what a description says")
    t = describe.describe(ROOT / "devices" / "ideas" / "tannin" / "Tannin.amxd")
    root = next(q for q in t["parameters"] if q["name"] == "Root")
    expect(t["device"]["kind"] == "midi_effect" and root["default"] == "A" and root["options"][:3] == ["C", "C#", "D"]
           and root["push"] == {"page": "Tannin", "slot": 1} and root["about"].startswith("The key's root"),
           "Tannin's Root: a MIDI effect's choice of 12, starting on A, Push's first slot, with its Info View text")
    m = describe.describe(ROOT / "devices" / "ideas" / "madder" / "another device.amxd")
    curved = [q for q in m["parameters"] if "curve" in q]
    expect(m["device"]["about"].startswith("Four engines") and curved and all(q["type"] != "choice" for q in curved)
           and any(q.get("unit") for q in m["parameters"]),
           f"another device: its Info text, units, and {len(curved)} knobs on a curve")
run = subprocess.run([sys.executable, str(TOOLS / "describe.py"), "--schema"], capture_output=True, text=True)
expect(json.loads(run.stdout) == schema, "describe.py --schema prints schema.json")
print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
