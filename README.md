# Max for Live tools

Two small tools for Max for Live devices, Python 3.8 or newer, standard library only. Neither needs Live or Max.

- **[Push 3 standalone check](STANDALONE.md)** (`standalone_check.py`): what in a device may not run on Push 3 in
  Standalone Mode, and what Push can't reach. Every rule is labelled by how sure it is, with its source
  ([RULES.md](RULES.md)).
- **[Device descriptions](SCHEMA.md)** (`describe.py`): a device's parameters as JSON, with what each one does, its
  unit, range, curve, default and Push page, for a language model or a controller script ([schema.json](schema.json)).

```sh
python3 standalone_check.py "My Device.amxd"
python3 describe.py "My Device.amxd" > "My Device.json"
```

Seen a device object run, or fail, on Push 3 standalone? Open an issue: that is how the check's list grows.

## Licence

MIT: see [LICENSE](LICENSE). Issues are welcome; pull requests by invitation ([CONTRIBUTING.md](CONTRIBUTING.md)).

Ableton, Live, Push and Max for Live are trademarks of Ableton AG. Max is a trademark of Cycling '74. This is an independent project, not affiliated with or endorsed by these companies.
