#!/usr/bin/env python3
"""The Push 3 standalone check (tools/m4l-tools/standalone_check.py): on a made-up device with each thing it looks
for, frozen and not, inside subpatchers and abstractions; on every device here; its rules as RULES.md has them."""

import json
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "m4l-tools" if (ROOT / "tools" / "m4l-tools").is_dir() else ROOT    # here, or on its own
sys.path.insert(0, str(TOOLS))
import standalone_check as check  # noqa: E402

failures = []


def expect(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


def obj(i, text, **kw):
    return {"box": dict(id=i, maxclass="newobj", text=text, **kw)}


def ui(i, cls, longname=None, **kw):
    box = dict(id=i, maxclass=cls, presentation=1, **kw)
    if longname:
        box.update(parameter_enable=1, saved_attribute_attributes={"valueof": {"parameter_longname": longname}})
    return {"box": box}


SUB = {"boxes": [obj("v", "vst~ 2 2"), obj("x", "fancy.ext~ 3"), obj("n", "node.script walk.js"),
                 obj("t", "*~ 0.5"), obj("g", "gen~", patcher={"boxes": [obj("gg", "notamaxobject")]})]}
PATCH = {"boxes": [obj("p", "p inner", patcher=SUB), obj("a", "myabs"), ui("d", "dial"),
                   ui("k", "live.dial", "Cutoff"), ui("q", "live.dial", "Res"), ui("r", "live.drop")],
         "dependency_cache": [{"name": "fancy.ext~.mxo", "type": "iLaX"}, {"name": "kick.wav", "type": "WAVE"}],
         "parameters": {"parameterbanks": {"0": {"index": 0, "name": "Main", "parameters": ["Cutoff", "-"]}}}}
ABS = {"patcher": {"boxes": [obj("w", "jit.window out"), obj("m", "metro 10")]}}


def field(tag, data):
    return tag + struct.pack(">I", 8 + len(data)) + data


def amxd(ptch):
    return b"ampf" + struct.pack("<I", 4) + b"aaaa" + b"meta" + struct.pack("<II", 4, 7) + b"ptch" \
        + struct.pack("<I", len(ptch)) + ptch


def frozen(files):
    """A frozen device's bytes, as Max's Freeze Device writes one: files [(name, bytes, flag)], the device first."""
    body, dirs = b"", b""
    for name, data, flag in files:
        raw = name.encode() + b"\x00" * (4 - len(name.encode()) % 4)
        dirs += field(b"dire", field(b"type", b"JSON") + field(b"fnam", raw)
                      + field(b"sz32", struct.pack(">I", len(data))) + field(b"of32", struct.pack(">I", 16 + len(body)))
                      + field(b"vers", bytes(4)) + field(b"flag", struct.pack(">I", flag)) + field(b"mdat", bytes(4)))
        body += data
    return amxd(b"mx@c" + struct.pack(">III", 16, 0, 16 + len(body)) + body + field(b"dlst", dirs))


def write(folder):
    body = json.dumps({"patcher": PATCH}).encode() + b"\x00"
    plain, fz = folder / "Plain.amxd", folder / "Frozen.amxd"
    plain.write_bytes(amxd(body))                                     # not frozen: the patcher, then a NUL
    fz.write_bytes(frozen([("Frozen.amxd", body, 17), ("myabs.maxpat", json.dumps(ABS).encode(), 0)]))
    return plain, fz


def table(found):
    return {(f[0], f[1], f[2], f[3]) for f in found}


print("a made-up device with each thing the check looks for")
with tempfile.TemporaryDirectory() as tmp:
    plain, fz = write(Path(tmp))
    got = table(check.check(plain))
    R, P = check.RUN, check.REACH
    want = {("documented", R, "vst~", "p inner"), ("likely", R, "fancy.ext~", "p inner"),
            ("check", R, "node.script", "p inner"), ("likely", R, "myabs", "top"), ("check", R, "live.drop", "top"),
            ("likely", R, "fancy.ext~.mxo", "dependencies"), ("check", R, "kick.wav", "dependencies"),
            ("documented", P, "dial", "top"), ("likely", P, "Res", "Push pages")}
    expect(got == want, "a plug-in host, an external (by name, and in the dependencies), Node for Max, an "
           "abstraction left outside, a file drop, a sample not frozen in, a mouse-only dial and a parameter on no "
           "Push page: each found once, where it sits, with its label; *~ is Max's, and gen~'s code isn't looked "
           "into" + ("" if got == want else f": missing {want - got}, extra {got - want}"))
    gotf = table(check.check(fz))
    expect(("check", R, "jit.window", "myabs") in gotf and ("likely", R, "myabs", "top") not in gotf
           and ("check", R, "kick.wav", "dependencies") in gotf,
           "frozen: the abstraction inside the device is opened and its jit.window found there")
    run = subprocess.run([sys.executable, str(TOOLS / "standalone_check.py"), "--json", str(plain)],
                         capture_output=True, text=True)
    out = json.loads(run.stdout)
    expect(run.returncode == 1 and out[0]["findings"][0].keys() == {"label", "kind", "object", "where", "what",
                                                                     "source"},
           "exit 1 when something documented or likely may not run; --json gives each finding's fields")
    check.VERIFIED["node.script"] = "Oct 27, Push OS 2.0, a test device"
    expect(("verified", R, "node.script", "p inner") in table(check.check(plain)),
           "an object seen working on Push is labelled verified")
    check.VERIFIED.clear()

paths = sorted((ROOT / "devices").rglob("*.amxd"))
if paths:
    print("every device here")
    runs = [f for p in paths for f in check.check(p) if f[0] in ("documented", "likely") and f[1] == check.RUN]
    expect(not runs, f"none of the {len(paths)} devices has anything documented or likely not to run on Push 3 "
           "standalone" + (f": {runs[:3]}" if runs else ""))

print("the rules")
rules = (TOOLS / "RULES.md").read_text()
m = re.search(r"<!-- generated: standalone_check.py --rules -->\n(.*?)\n<!-- end of generated -->", rules, re.S)
expect(m is not None and m.group(1) == check.rules_md(),
       "RULES.md's table is the check's own (standalone_check.py --rules)")
expect(all(src.startswith("https://") for _, _, src in check.RULES.values() if src)
       and all(lab != "documented" or src for lab, _, src in check.RULES.values()),
       "every documented rule names its source")
print(f"\n{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
