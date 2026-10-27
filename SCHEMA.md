# Device descriptions

A language model asked to "make the delay darker" sees a device the way Live's API shows it: names, numbers
between a minimum and a maximum, and whether each is a whole number. It doesn't know that `Tone` is a low-pass in
Hz on a curve, that `Mode` has four options, or which of thirty parameters are the eight that matter. A device
description adds that, from the device file itself.

```sh
python3 describe.py "My Device.amxd" > "My Device.json"
```

## What's in one

```json
{
 "format": "m4l-device-description",
 "version": "0.1",
 "device": {"name": "Tannin", "kind": "midi_effect", "about": null},
 "parameters": [
  {"name": "Root", "short_name": "Root", "about": "The key's root, for every family device on Tannin key",
   "type": "choice", "visibility": "automatable", "options": ["C", "C#", "D", "..."], "default": "A",
   "push": {"page": "Tannin", "slot": 1}}
 ],
 "push_pages": [{"name": "Tannin", "parameters": ["Root", "Scale", "From Live", null, null, null, null, null]}]
}
```

[schema.json](schema.json) is the JSON Schema; each field in short:

| Field | What it says | From |
| --- | --- | --- |
| `device.about` | what the device is and how to start | the device's Info text (the top patcher's description) |
| `name` | the parameter's long name: what Live's API, automation and mappings call it | `parameter_longname` |
| `short_name` | what Push and the panel show | `parameter_shortname` |
| `about` | what it does, in the builder's words | the control's Info View text (`annotation`) |
| `type` | `continuous`, `integer` or `choice` | `parameter_type` |
| `range`, `unit` | min and max, and what the number means (ms, Hz, dB, %, pan, semitones, MIDI note, or `custom` with `unit_format`) | `parameter_mmin`, `parameter_mmax`, `parameter_unitstyle`, `parameter_units` |
| `curve` | the knob's exponent: value = min + (max - min) * position ^ curve | `parameter_exponent` |
| `options` | a choice's options in order (its value is the index) | `parameter_enum` |
| `default` | where it starts | `parameter_initial` |
| `visibility` | `automatable` (automation, mapping and Push reach it), `stored` or `hidden` | `parameter_invisible` |
| `push` | its page and slot on Push, or null | the device's Push pages (`parameterbanks`) |

A device with no Info View text still gets everything but the `about` fields. The more a builder writes in Max's
Info View fields, the more a model knows.

## With Live's API

Live's API (and so [AbletonOSC](https://github.com/ideoforms/AbletonOSC)'s `/live/device/get/parameters/name`,
`.../min`, `.../max`, `.../is_quantized` and `.../value_string`) gives each parameter's name, range and value. A
description is matched to a device in a set by its name, and to each parameter by `name`; Live's API sets values
in the parameter's own range, which `range` gives. What a description adds is the meaning: `about`, `unit`,
`curve`, `options`, `default` and the Push pages, which say which parameters a player reaches first.

The format is a draft (0.1). Fields may be added; none will change meaning without a new version.
