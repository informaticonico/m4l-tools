#!/usr/bin/env python3
"""Push 3 standalone check: what in a Max for Live device may not run on Push 3 in Standalone Mode.

    python3 tools/m4l-tools/standalone_check.py Device.amxd [more.amxd or folders...]
    python3 tools/m4l-tools/standalone_check.py --json Device.amxd      the findings as JSON
    python3 tools/m4l-tools/standalone_standalone_check.py --rules                 the rules, as RULES.md has them
    python3 tools/m4l-tools/standalone_check.py --refresh               rebuild max_objects.json (needs the network)

It reads the device's patcher (frozen or not) and every patcher inside it: subpatchers, bpatchers and
abstractions frozen into the device. gen~ and rnbo~ code isn't Max objects and isn't looked into.

Each finding has a label that says how sure it is:

    documented   Ableton or Cycling '74 says so
    likely       follows from what they say (an external is code built for one computer's system)
    check        nobody has said either way: try it on Push before you promise it runs there

Nothing here is verified on a Push yet: when an object is seen working there, it goes in VERIFIED, with
the date and Push OS version, and the check says so. Findings are of two kinds: what may not run on Push,
and what runs but is out of Push's reach (a control only a mouse can turn). Exit 1 when a device has a
documented or likely finding of the first kind. Python 3.8 or newer, standard library only.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from amxd import read_device

HERE = Path(__file__).resolve().parent
OBJECTS = HERE / "max_objects.json"
SITEMAP = "https://docs.cycling74.com/sitemap.xml"

ABLETON_FAQ = "https://www.ableton.com/en/push/tech-specs/"
ABLETON_M4L = "https://help.ableton.com/hc/en-us/articles/8506527153308"
C74_EXTERNALS = "https://docs.cycling74.com/userguide/externals/"
C74_PARAMETERS = "https://docs.cycling74.com/userguide/m4l/live_parameters/"
C74_FILES = "https://docs.cycling74.com/userguide/m4l/live_files/"

# object -> (label, what happens, source). Lean on purpose: only what a source supports, or what
# nobody has answered and a builder should test.
RULES = {
    "vst~": ("documented", "hosts a VST or AU plug-in: Push doesn't support VSTs or Audio Unit plug-ins in "
                           "Standalone Mode", ABLETON_FAQ),
    "node.script": ("check", "Node for Max runs a separate Node.js process; nothing says whether Push starts "
                             "one", ""),
    "mxj": ("check", "Java (mxj): nothing says whether Push has Java", ""),
    "mxj~": ("check", "Java (mxj~): nothing says whether Push has Java", ""),
    "jweb": ("check", "a web browser in the panel: nothing says whether Push has one", ""),
    "jit.window": ("check", "opens a window: Push has no screen for it", ""),
    "jit.world": ("check", "opens a window: Push has no screen for it", ""),
    "rnbo~": ("check", "RNBO is a package, not part of Max: nothing says whether Push has it", ""),
    "live.drop": ("check", "takes a dropped file: Ableton lists 'sample import disabled' among the limits of "
                           "some devices on Push", ABLETON_M4L),
    "dropfile": ("check", "takes a dropped file: there is no mouse or file browser on Push", ABLETON_M4L),
    "opendialog": ("check", "opens a file dialog: Push has none", ""),
    "savedialog": ("check", "opens a file dialog: Push has none", ""),
}

# Controls a player can only reach with a mouse unless they are parameters (Push shows parameters only).
UI = {"dial", "slider", "toggle", "number", "flonum", "umenu", "multislider", "kslider", "nslider", "pictslider",
      "rslider", "matrixctrl", "textbutton", "tab", "radiogroup", "incdec", "live.dial", "live.slider",
      "live.numbox", "live.menu", "live.tab", "live.text", "live.toggle", "live.button"}
LIVE_UI = {u for u in UI if u.startswith("live.")}

# Seen working on Push 3 standalone: object -> "date, Push OS version, device it ran in". Empty until
# someone checks one.
VERIFIED = {}

# Max's operators the reference spells out (times~ for *~): not in the sitemap under their own names
OPERATORS = {"+~", "-~", "*~", "/~", "!-~", "!/~", "%~", "<~", ">~", "<=~", ">=~", "==~", "!=~", "+=~"}

NOT_INTO = {"gen~", "gen", "rnbo~", "jit.gen", "jit.pix", "jit.gl.pix", "mc.gen~"}
FILE_ARGS = {"bpatcher", "poly~", "pfft~", "mc.poly~"}


def known_objects():
    return set(json.loads(OBJECTS.read_text())["objects"]) | OPERATORS


def object_class(box):
    if box.get("maxclass") != "newobj":
        return box.get("maxclass", "")
    return (box.get("text") or "").split(" ")[0]


def walk(patcher, files, where=(), seen=None):
    """Every box, with where it sits: (box, ("subpatcher", ...)). Frozen abstractions are opened."""
    seen = set() if seen is None else seen
    for b in patcher.get("boxes", []):
        box = b["box"]
        yield box, where
        cls = object_class(box)
        if cls in NOT_INTO:
            continue
        inner = box.get("patcher")
        label = box.get("varname") or box.get("text") or cls
        if inner is None:
            name = _abstraction(box, cls, files)
            if name and name not in seen:
                seen.add(name)
                try:
                    inner = json.loads(files[name].rstrip(b"\x00"))["patcher"]
                except (ValueError, KeyError):
                    inner = None
        if inner is not None:
            yield from walk(inner, files, where + (label,), seen)


def _abstraction(box, cls, files):
    """The frozen file a box opens, if it opens one."""
    words = (box.get("text") or "").split(" ")
    cands = [cls]
    if cls in FILE_ARGS:
        cands = [box.get("name", "")] + words[1:2]
    for c in cands:
        for name in (c, c + ".maxpat"):
            if c and name in files and name.endswith((".maxpat", ".json")):
                return name
    return None


# --- the check ------------------------------------------------------------------------------------------

RUN, REACH = "may not run", "out of Push's reach"


def check(path, objects=None):
    """[(label, kind, object, where, what, source)] for one device: kind is RUN (the device, or part of it, may
    not load or work on Push) or REACH (it works, but Push can't reach the control)."""
    objects = known_objects() if objects is None else objects
    patcher, files = read_device(path)
    found, params, banked = [], [], None
    for box, where in walk(patcher, files):
        cls = object_class(box)
        at = " > ".join(where) or "top"
        if cls in RULES:
            label, what, src = RULES[cls]
            if cls in VERIFIED:
                label, what = "verified", f"{what} (seen working on Push: {VERIFIED[cls]})"
            found.append((label, RUN, cls, at, what, src))
        elif cls and cls not in objects and not _abstraction(box, cls, files) and cls not in NOT_INTO:
            found.append(("likely", RUN, cls, at, "not a Max object and not a file inside the device: an external "
                          "(code built for one computer's system, .mxo or .mxe64) or an abstraction left "
                          "outside the device; Push may not load it", C74_EXTERNALS))
        if cls in UI and box.get("presentation"):
            if box.get("parameter_enable") or (cls in LIVE_UI and "parameter_enable" not in box):
                if _valueof(box).get("parameter_invisible", 0) not in (1, 2):
                    params.append(_longname(box))
            else:
                found.append(("documented", REACH, cls, at, "a control on the panel that isn't a parameter: Live, "
                              "and so Push, shows parameters only (fine if it only changes what the panel shows)",
                              C74_PARAMETERS))
    for d in patcher.get("dependency_cache", []):
        n = d.get("name", "")
        if d.get("type") == "iLaX" or n.endswith((".mxo", ".mxe", ".mxe64")):
            found.append(("likely", RUN, n, "dependencies", "an external the device needs: built for one computer's "
                          "system; Push may have no build of it", C74_EXTERNALS))
        elif n not in files and not n.endswith(".amxd"):
            found.append(("check", RUN, n, "dependencies", "a file the device needs that isn't frozen into it: copy "
                          "it to Push too, or freeze the device", C74_FILES))
    banks = patcher.get("parameters", {}).get("parameterbanks")
    if banks:
        banked = {n for b in banks.values() for n in b.get("parameters", []) if n and n != "-"}
        for n in params:
            if n and n not in banked:
                found.append(("likely", REACH, n, "Push pages", "a control on the panel that is on none of the "
                              "device's Push pages: Push shows the pages the device defines", C74_PARAMETERS))
    return found


def _valueof(box):
    return box.get("saved_attribute_attributes", {}).get("valueof", {})


def _longname(box):
    return _valueof(box).get("parameter_longname") or box.get("varname", "")


def devices(args):
    for a in args:
        p = Path(a)
        yield from (sorted(p.rglob("*.amxd")) if p.is_dir() else [p])


ORDER = {"documented": 0, "likely": 1, "check": 2, "verified": 3}


def report(path, found):
    lines = [f"{path}"]
    if not found:
        lines.append("  nothing found: no object here is known to fail on Push 3 standalone (not a promise: "
                     "try it there)")
    for kind in (RUN, REACH):
        mine = sorted((f for f in found if f[1] == kind), key=lambda f: (ORDER[f[0]], f[2], f[3]))
        if mine:
            lines.append(f"  {kind}:")
        for label, _, obj, at, what, src in mine:
            lines.append(f"    {label:<10} {obj}  ({at}): {what}" + (f"  [{src}]" if src else ""))
    return "\n".join(lines)


def rules_md():
    rows = ["| Object | Label | What happens | Source |", "| --- | --- | --- | --- |"]
    for obj, (label, what, src) in sorted(RULES.items(), key=lambda kv: (ORDER[kv[1][0]], kv[0])):
        rows.append(f"| `{obj}` | {label} | {what} | {src or '-'} |")
    rows.append(f"| any object not among Max's {len(known_objects())} | likely | an external (built for one "
                f"computer's system) or an abstraction left outside the device | {C74_EXTERNALS} |")
    rows.append(f"| a panel control that isn't a parameter | documented | Push shows parameters only | "
                f"{C74_PARAMETERS} |")
    rows.append(f"| a parameter on the panel but on none of the Push pages | likely | Push shows the pages the "
                f"device defines | {C74_PARAMETERS} |")
    return "\n".join(rows)


def refresh():
    with urllib.request.urlopen(SITEMAP, timeout=60) as r:
        xml = r.read().decode("utf-8")
    locs = [part.split("</loc>")[0] for part in xml.split("<loc>")[1:]]
    names = sorted({urllib.parse.unquote(loc.split("/reference/", 1)[1].rstrip("/"))
                    for loc in locs if "/reference/" in loc} - {""})
    OBJECTS.write_text(json.dumps({"source": f"{SITEMAP} (every page under /reference/)",
                                   "fetched": __import__("datetime").date.today().isoformat(),
                                   "objects": names}, indent=0) + "\n")
    print(f"wrote {OBJECTS.name}: {len(names)} objects")


def main(argv):
    if "--refresh" in argv:
        refresh()
        return 0
    if "--rules" in argv:
        print(rules_md())
        return 0
    paths = list(devices(a for a in argv if not a.startswith("--")))
    if not paths:
        print(__doc__)
        return 2
    objects, bad, out = known_objects(), False, []
    for p in paths:
        found = check(p, objects)
        bad |= any(f[0] in ("documented", "likely") and f[1] == RUN for f in found)
        out.append((p, found))
    if "--json" in argv:
        keys = ("label", "kind", "object", "where", "what", "source")
        print(json.dumps([{"device": str(p), "findings": [dict(zip(keys, f)) for f in found]} for p, found in out],
                         indent=1))
    else:
        print("\n\n".join(report(p, found) for p, found in out))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
