# Vapor GTK 3.24 support

The maintained theme now targets GTK 3.24. The old folder name did not mean the
previous theme was incompatible: GTK 3.24 already loaded its gtk-3.20 stylesheet
through GTK's version fallback, and it parsed with zero errors. The changes
make the supported target explicit, remove obsolete styles and fix confirmed
selectors while preserving Vapor's colors and artwork.

## Selection palette update (1.0.2)

Valve's GTK stylesheet used Breeze blue independently of KDE's active colors.
The GTK 3.24 compatibility work did not cause or fix that mismatch. GTK now
matches Vapor.colors: **#569fcc** selection background with **#1f1f26** text.
The palette remains Vapor-specific; it does not dynamically follow arbitrary
KDE color schemes. Selected text and rows use that pair, while gradients,
alpha states, focus/hover borders, progress, switches and sliders derive their
accent from the same named GTK color.

The blue portions of 32 check/radio PNGs were remapped as well. For saturated
blue pixels near the original accent hue, hue is shifted by the old/new accent
difference and saturation/value scaled by their ratios. Alpha, image dimensions,
neutral outlines and dark glyphs are preserved. The remaining images are unchanged.
Unfocused windows: dimmed selections (text, entries, tree views; half-strength
blue over the view) use light **#eff0f1** text, 6.1:1. Rows that GTK keeps at
full strength when unfocused (activatable list rows, the places sidebar) keep
the dark **#1f1f26** text, 5.6:1; a `row.activatable:selected:backdrop label`
rule is needed because `label:backdrop` otherwise forces light text there.
The first palette pass used dark text everywhere (2.34:1 unfocused); fixed in
Claude Code's review, and check-gtk3.py now asserts >= 4.5:1 for both cases.

Link and semantic warning/error/success colors are unchanged. Original contrast
and alpha treatment of disabled/inactive states is preserved, using the new blue.

Regression checks now compare actual label/entry/list/tree style-context selection
colors to Vapor.colors, assert ordinary button text is unchanged, decode all PNGs,
reject old solid Breeze blue in artwork and require the new blue. Both stylesheet
entries parse; discovery and all six window states/eight indicator renders pass.
This supersedes the palette-preservation statements in the historical port
verification below. The local changes have not been installed or released.

## Layout and fixes

- `usr/share/themes/Vapor/gtk-3.24/gtk.css`: maintained GTK 3.24 stylesheet.
- `usr/share/themes/Vapor/gtk-3.0/gtk.css`: relative import of that stylesheet
  for theme choosers and direct consumers expecting the standard GTK 3 entry.
- Removed gtk-3.18 and gtk-3.20 folders. The former used an obsolete selector
  model and referenced 12 absent scrollbar images. Its source remains in Git.
- Three `label:backdrop selction` typos now name the `selection` CSS node.
  An isolated label/selection context changed from opaque blue to the existing
  intended rgba(61,174,233,0.5). No new color was introduced.
- `scale.fine-tune.trough` is deliberately left as upstream Breeze GTK 6.8 still
  has it. It never matches (fine-tune is a class on the scale, not the trough),
  so sliders keep their 9px trough margin during GTK's fine-tune (zoom) drag.
  Making the 8px apply would shrink the slider 2px mid-drag; Claude Code
  reverted that change in review (2026-10-29). Vertical scale selectors put the
  orientation class on the scale ancestor, not on trough/highlight children;
  those rules repeat the general values, so nothing renders differently.
- The 110 image assets the stylesheet references are kept; 56 unreferenced
  ones were removed in review (16 only used by the deleted gtk-3.18, 40 already
  unused). Named colors, regular widget styling and previous checkbox/radio
  image fixes are preserved. There is no Breeze GTK dependency
  or import. GTK 2, GTK 3 older than 3.24, and GTK 4 are outside this target.

## Verification

Run from the repository root:

```sh
python3 -I tools/check-gtk3.py
```

Requirements: `gtk3` (with broadwayd), `python-gobject`, `python-cairo`, `python-pillow`, and
fonts (the fixture selects DejaVu Sans). An optional `--output /tmp/vapor-gtk`
keeps the captures; otherwise every test output is temporary. `--theme PATH`
can validate another unpacked theme directory. `--baseline` is only for
comparison to the previous gtk-3.20 layout and skips the new selector assertions.

The test creates a private Broadway server whose HTTP listener is a Unix
socket, not a network port. Temporary HOME/XDG config, cache, data, state and
runtime paths, a disconnected session bus and the memory settings backend keep
the active desktop isolated. The staged CSS gets an unused named-color marker
so the test can assert the named loader and actual widgets use its fixture,
rather than an installed copy of Vapor. No user theme or settings are changed.

Checks on GTK 3.24.52:

- Both entry stylesheets parse without errors; every CSS URL resolves.
- Normal and requested dark variants select the same Vapor stylesheet, without
  falling through to another installed theme. Vapor is already dark.
- Regression assertions cover inactive label selection, the upstream 9px
  fine-tune margin, and no unreferenced assets.
- Real offscreen controls: buttons/toggles, entry, checkbox/radio and mixed
  states, switch, horizontal/vertical scales and spin buttons, progress,
  combo box, notebook, selectable label, text view, level bar, selected list
  row and modelbutton check/radio indicators. Normal, hover, backdrop,
  right-to-left, fine-tuning and disabled snapshots render without GTK warnings.
- Compared with the prior source on the same backend: normal, hover, disabled
  and right-to-left sample windows are pixel-identical. Backdrop has 1,126
  changed pixels in the selectable label. Fine-tuning keeps the previous
  geometry (the margin change was reverted). Other geometry/colors retained.
- Eight separate GTK check/radio renders cover checked and mixed-hover states
  at style-context scales 1 and 2. They are nonblank and pixel-identical to
  the baseline, with the existing @2 artwork references intact.

The Broadway display's window scale factor is 1. Scale-2 indicator tests use
GTK's scaled style contexts plus Cairo; they do not validate a complete HiDPI
window. Live Wayland/X11, real HiDPI monitors, application-specific CSS,
accessibility interactions and long-running performance remain untested.
This is GTK 3.24 compatibility work, not GTK 4/libadwaita support.

## Packaging and status

Released as 1.0.2 (tag v1.0.2, AUR `plasma6-themes-steamos-vapor-fixed`
1.0.2-1). Later changes need a new version, archive checksum and AUR metadata.
Replacing the whole theme directory removes
old versioned subdirectories during a manual upgrade; do not merge directories.
Pacman will remove old package-owned files during a packaged upgrade.

References:

- [GTK 3.24 theme loading and version fallback](https://docs.gtk.org/gtk3/class.CssProvider.html)
- [GTK CSS nodes and selectors](https://docs.gtk.org/gtk3/css-overview.html)
- [GTK Scale CSS nodes](https://docs.gtk.org/gtk3/class.Scale.html)
- [GTK Label selection node](https://docs.gtk.org/gtk3/class.Label.html)


## Inactive-control regressions (1.0.3)

The regular checker now invokes tools/check-gtk-regressions.py for checked/
pressed child-label contrast and spin-arrow background checks. The normal and
inactive horizontal/vertical range/disabled matrix protects Claude's image-layer
reset. Run `python3 -I tools/test-gtk-regressions.py` to prove the guards reject
six deliberately reverted fixes across GTK 3/4. This extra proof needs both
installed toolkit test environments. See gtk4port.md section 10 for details.
