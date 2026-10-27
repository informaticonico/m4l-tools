"""Reading a Max for Live device (.amxd): its patcher, and the files frozen into it.

A device is a small header ('ampf', its kind, 'meta'), then 'ptch': either the patcher's JSON with a NUL at its end,
or, frozen, an 'mx@c' block holding each file's bytes and a directory ('dlst') naming them; the device's own
patcher has flag 17. Standard library only.
"""

import json
import struct
from pathlib import Path

KINDS = {b"aaaa": "audio_effect", b"mmmm": "midi_effect", b"iiii": "instrument"}


def _fields(data):
    out, i = [], 0
    while i < len(data):
        (size,) = struct.unpack(">I", data[i + 4:i + 8])
        out.append((data[i:i + 4], data[i + 8:i + size]))
        i += size
    return out


def read_device(path):
    """(the device's patcher, {name: bytes} of the files frozen into it)."""
    data = Path(path).read_bytes()
    if data[:4] != b"ampf" or data[24:28] != b"ptch":
        raise ValueError(f"{path}: not a Max for Live device")
    (size,) = struct.unpack("<I", data[28:32])
    ptch = data[32:32 + size]
    if ptch[:4] != b"mx@c":                            # not frozen: the patcher's JSON, then a NUL
        return json.loads(ptch.rstrip(b"\x00"))["patcher"], {}
    (dlst,) = struct.unpack(">I", ptch[12:16])
    main, files = None, {}
    for _, dire in _fields(ptch[dlst + 8:]):
        f = dict(_fields(dire))
        (sz,), (off,), (flag,) = (struct.unpack(">I", f[k]) for k in (b"sz32", b"of32", b"flag"))
        name, body = f[b"fnam"].rstrip(b"\x00").decode("utf-8"), ptch[off:off + sz]
        if flag == 17 and main is None:
            main = json.loads(body.rstrip(b"\x00"))["patcher"]
        else:
            files[name] = body
    return main, files


def device_kind(path):
    """'audio_effect', 'midi_effect' or 'instrument'."""
    return KINDS.get(Path(path).read_bytes()[8:12], "unknown")


def boxes(patcher):
    """Every box in a patcher and its subpatchers."""
    for b in patcher.get("boxes", []):
        yield b["box"]
        if "patcher" in b["box"]:
            yield from boxes(b["box"]["patcher"])
