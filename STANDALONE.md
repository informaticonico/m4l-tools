# Push 3 standalone check

Will a Max for Live device run on Push 3 in Standalone Mode? This reads the device, and every patcher inside it,
and lists what may not run there and what Push can't reach. It runs on your computer, without Live or Max.

```sh
python3 standalone_check.py "My Device.amxd"          # one device
python3 standalone_check.py ~/Music/Ableton/User\ Library/Presets   # every device in a folder
python3 standalone_check.py --json "My Device.amxd"   # the findings as JSON
python3 standalone_check.py --rules                   # what it looks for
```

A finding looks like this:

```
My Device.amxd
  may not run:
    likely     fancy.ext~  (p inner): not a Max object and not a file inside the device: an external ...
    check      node.script  (p inner): Node for Max runs a separate Node.js process; nothing says whether Push starts one
  out of Push's reach:
    documented dial  (top): a control on the panel that isn't a parameter: Live, and so Push, shows parameters only ...
```

Each finding is labelled by how sure it is: **documented** (Ableton or Cycling '74 says so, with the link),
**likely** (follows from what they say), **check** (nobody has said: try it on a Push) or **verified** (seen
working on a Push). [RULES.md](RULES.md) has every rule and its source. "Nothing found" means nothing here is known
to fail, not that the device is guaranteed to run: Ableton guarantees no third-party device.

It exits 1 when a device has something documented or likely not to run, so it can sit in a build.

Python 3.8 or newer, standard library only. `max_objects.json` lists Max's 1,800-odd objects, from Cycling '74's
reference; `python3 standalone_check.py --refresh` rebuilds it.
