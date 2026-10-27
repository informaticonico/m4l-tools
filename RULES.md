# What the check looks for

A lean list on purpose. Ableton says only that most of its own Max for Live devices run on Push 3 in Standalone
Mode, "as will many third-party devices", and that "translating objects for Push is very complex, so we can't
guarantee that all Max for Live devices (including your self-built patches) will work as expected" (the Push
[tech specs and FAQ](https://www.ableton.com/en/push/tech-specs/)). A device that uses an object Push can't run
shows a "missing or incompatible Max objects" error there (Ableton's
[compatibility article](https://help.ableton.com/hc/en-us/articles/8506527153308)). Nobody has published which
objects those are, so each rule carries a label:

- **documented**: Ableton or Cycling '74 says so, and the source is named.
- **likely**: follows from what they say. An external is executable code built for one computer's system (`.mxo`
  on a Mac, `.mxe64` on Windows: [Cycling '74](https://docs.cycling74.com/userguide/externals/)); Push 3 runs on
  its own Intel computer, so a third-party external may have no build for it.
- **check**: nobody has said either way. Try it on a Push before promising it runs there.
- **verified**: seen working on a Push (with the date and Push OS version). None yet: add one to `VERIFIED` in
  `standalone_check.py` when a check comes back.

Findings are of two kinds: what **may not run** on Push, and what runs but is **out of Push's reach** (Push shows a
device's parameters, on its pages, and nothing else).

<!-- generated: standalone_check.py --rules -->
| Object | Label | What happens | Source |
| --- | --- | --- | --- |
| `vst~` | documented | hosts a VST or AU plug-in: Push doesn't support VSTs or Audio Unit plug-ins in Standalone Mode | https://www.ableton.com/en/push/tech-specs/ |
| `dropfile` | check | takes a dropped file: there is no mouse or file browser on Push | https://help.ableton.com/hc/en-us/articles/8506527153308 |
| `jit.window` | check | opens a window: Push has no screen for it | - |
| `jit.world` | check | opens a window: Push has no screen for it | - |
| `jweb` | check | a web browser in the panel: nothing says whether Push has one | - |
| `live.drop` | check | takes a dropped file: Ableton lists 'sample import disabled' among the limits of some devices on Push | https://help.ableton.com/hc/en-us/articles/8506527153308 |
| `mxj` | check | Java (mxj): nothing says whether Push has Java | - |
| `mxj~` | check | Java (mxj~): nothing says whether Push has Java | - |
| `node.script` | check | Node for Max runs a separate Node.js process; nothing says whether Push starts one | - |
| `opendialog` | check | opens a file dialog: Push has none | - |
| `rnbo~` | check | RNBO is a package, not part of Max: nothing says whether Push has it | - |
| `savedialog` | check | opens a file dialog: Push has none | - |
| any object not among Max's 1831 | likely | an external (built for one computer's system) or an abstraction left outside the device | https://docs.cycling74.com/userguide/externals/ |
| a panel control that isn't a parameter | documented | Push shows parameters only | https://docs.cycling74.com/userguide/m4l/live_parameters/ |
| a parameter on the panel but on none of the Push pages | likely | Push shows the pages the device defines | https://docs.cycling74.com/userguide/m4l/live_parameters/ |
<!-- end of generated -->

The list of Max's objects (`max_objects.json`) is every page under `/reference/` in Cycling '74's sitemap, with
the operators the reference spells out (`times~` for `*~`). `python3 standalone_check.py --refresh` rebuilds it.

Seen something run, or fail, on Push 3 standalone? Open an issue with the object, the Push OS version and what
happened. That is how a rule moves from **check** to **verified** or **documented**.
