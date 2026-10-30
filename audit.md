# Manual 4K / 175% scaling check — 2026-10-30

The user tested Vapor with the installed GTK Widget Factory on a 4K monitor
set to 175% scaling and reported: "everything looked good".

**Result: user-reported visual pass for that display configuration.** This adds
live application coverage alongside the isolated automated suite below. No theme
fix was indicated by this check. Exact renderer/session details and individual
control results were not captured, so this is not a separate certification of
every focus/popup state, GPU backend or scaling configuration.

Broader interaction, other display/scaling configurations, accessibility,
animation/performance and wider application coverage remain open. The automated
suite itself still uses Broadway/Cairo at scale 1. See gtk4port.md section 13.

---

# Installed GTK Widget Factory verification — 2026-10-30

Agent: Codex (GPT-6). Base: clean `1f0b925` after release 1.0.3. User requested
automated testing with the newly installed GTK Widget Factory, then requested
including it in the standard suite. This work changes test tools and
documentation only.

- The standard `tools/check-gtk4.py` entry point runs all ten application cases
  after native widget/parser checks and R1/R2 behavior checks. It forwards
  `--theme`, places application `--output` evidence under `widget-factory/` and
  propagates failures, including missing dependencies. No automatic skip.

- `tools/check-widget-factory.py` compiles a temporary C helper and loads it
  only into the installed `/usr/bin/gtk4-widget-factory` child. It drives the
  actual application stack on private Broadway/D-Bus with temporary HOME/XDG
  paths, staged Vapor and software rendering. The application's own CSS remains
  active. No existing desktop input, application actions or settings changes.
- **10 cases pass on GTK 4.24.1:** all three pages in normal and dark requests,
  all three with synthetic backdrop, plus page 1 in RTL. Each page is 1215x705;
  mapped-widget counts are 320 / 227 / 431 respectively. These counts include
  internal widgets and are not counts of distinct user-facing controls.
- Assertions cover the staged theme's unused marker, #569fcc/#1f1f26 selection
  definitions, requested/effective page/state/direction, mapped controls,
  correctly sized, opaque, nonblank PNGs and distinct first-three-page images.
  This does not assert every control's computed color; the existing focused
  widget/regression suites retain that responsibility.
- Negative controls reject a disposable wrong-blue theme with the specific
  `wrong selection blue` failure and a disposable unknown CSS property with
  its parser warning. Strict mode also rejects the known warning below.
- **Known backend diagnostic:** page 3 emits
  `gdk_frame_timings_submitted() called on submitted frame.` once per run.
  It reproduces with a minimal stylesheet containing only two named colors
  and no Vapor rules, before capture, including under a debugger. Thus it is
  not evidence of a Vapor CSS defect. The normal run preserves/counts only
  this exact diagnostic (three total); every other stderr diagnostic fails.
  `--strict` rejects it as well. The backend cause has not been fully diagnosed;
  these runs are not warning-free passes in strict mode.

Reproduce from the repository root:

```sh
python3 -I tools/check-gtk4.py --output /tmp/vapor-gtk4-standard-suite
```

Screenshots, raw per-case logs, binary/theme hashes and a machine-readable
report from the first standalone run were retained locally under
`/tmp/vapor-factory-d4yo6hy1/full`. The integrated standard suite also passes:
ten native-widget renders with zero parser errors, R1/R2 behavior assertions
(5.43:1 checked-label contrast and 32 flat spin backgrounds), and all ten
application cases with the same three known backend warnings. Integrated
application evidence is under `/tmp/vapor-gtk4-standard-suite/widget-factory`.
`gtk4port.md` sections 11–12 record implementation, experiments and integration.
No theme fix was needed for these assertions. The independent GTK 3 suite was
not repeated: its source and theme files are unchanged since its passing run.

Limits: content snapshots on Broadway/Cairo at scale 1 with synthetic states;
no keyboard/pointer input, open popup surfaces, live Wayland/GPU/HiDPI,
accessibility, animation/performance measurement or libadwaita coverage.

---

# R1/R2 fixes and verification — 2026-10-30

Agent: Codex (GPT-6). User requested fixing findings 1 and 2 from the review
below. **Both are now addressed locally**, with executable regression coverage.

- **R1 fixed, GTK 3 and GTK 4:** enabled checked/pressed button labels inherit
  their button foreground in backdrop state. The actual label is now #1f1f26,
  with measured gradient-sample contrast **5.37:1 on GTK 3 / 5.43:1 on GTK 4**,
  up from 2.67:1 / 2.65:1. Ordinary labels and insensitive checked controls retain
  their prior treatment; global label and dimmed text-selection rules are intact.
- **R2 fixed:** both existing toolkit suites now run
  `tools/check-gtk-regressions.py`. It checks native label colors/contrast and
  a horizontal/vertical, min/middle/max/disabled spin matrix in normal/backdrop.
  GTK 3 arrow buttons are CSS gadgets: background layers are rendered from
  matching GtkWidgetPath contexts through Cairo. GTK 4 checks real child-button
  sensitivity and rendered background strips. Each toolkit checks 32 flat spin
  backgrounds across the two states, rather than merely saving pictures.
- **Negative controls:** `tools/test-gtk-regressions.py` removes only the label
  override, horizontal spin reset, or vertical spin reset from disposable theme
  copies, separately on GTK 3/4. All six fail with the intended R1/R2 assertion.
  The test requires that specific AssertionError, not merely a nonzero exit.
- The new label regression failed on the old stylesheet before the CSS change.
  Complete GTK 3 and GTK 4 suites pass with both fixes; prior palette/contrast,
  image, discovery and ten GTK 4 rendering checks still pass.
- Work is documented in gtk4port.md section 10 and CHANGES.txt. Shared PNGs,
  colors outside the conditional foreground inheritance, kitty work, AUR recipe,
  installed files and session settings are unchanged. No commits or publication.

Reproduce:

```sh
python3 -I tools/check-gtk3.py
python3 -I tools/check-gtk4.py
python3 -I tools/test-gtk-regressions.py
```

Existing first-port limits remain: synthetic backdrop/normal-scale private
Broadway/Cairo checks, not live compositor focus/HiDPI or full GTK 4 coverage.
The review below records the state **before** these requested fixes.

---

# GTK 4 implementation review — Claude's spin-button fix

Date: **2026-10-30**, America/Phoenix. Reviewer: **Codex (GPT-6)**.
Audited base HEAD: `4abe95d19366a437144bc2f469657563c2d86baa`, plus the
uncommitted GTK 4 port and Claude's subsequent spin-button edits.
Scope: GTK 3/4 spin correction, current port behavior and regression coverage.
The unrelated kitty additions were left untouched and were not audited here.

**Verdict:** Claude's two `background-image: none` declarations per toolkit are
correct and narrowly scoped. No regression attributable to that fix was found.
The broader port still has the two issues below; neither was introduced by
Claude's spin-button change. Theme/test implementation files were not changed
by this review. The prior porting assessment is preserved later in this file.

## Findings

### R1 — P2: inactive checked-button labels still lose the correct foreground

Locations: `usr/share/themes/Vapor/gtk-4.0/gtk.css:174` (`label:backdrop`),
`:345` (`button:backdrop:checked`) and the GTK 3 counterpart
`usr/share/themes/Vapor/gtk-3.24/gtk.css:189`.

Trigger: an enabled GtkToggleButton is checked and its window becomes inactive.
The button correctly resolves to dark **#1f1f26**, but its actual child label
resolves to **#eff0f1** because the generic inactive-label rule overrides
inheritance. The background remains the full blue active gradient, so the label
is substantially less readable than intended.

Confirmed with real widgets on both toolkits, in both the fixed and reverted
spin-button variants:

| Toolkit | Button foreground | Actual label foreground | Sampled rendered blue | Light-label contrast |
| --- | --- | --- | --- | --- |
| GTK 3.24.52 | #1f1f26 | #eff0f1 | RGB 83,155,200 | **2.67:1** |
| GTK 4.24.1 | #1f1f26 | #eff0f1 | RGB 83,156,200 | **2.65:1** |

The sampled backgrounds are points in the existing gradient, not a new palette.
With the intended dark text those same samples give approximately 5.37:1 and
5.43:1. The current checker asserts ordinary-button and selected-row colors,
but not the checked button's child-label contrast; therefore it misses this.

Recommended follow-up: make enabled checked/active blue-filled button labels
inherit the button foreground in backdrop state, then assert the child label's
actual computed color and rendered contrast. Keep ordinary inactive labels and
half-alpha text selections light, and preserve insensitive-state treatment.
Do not replace the global `label:backdrop` rule indiscriminately.

This is an existing palette/inheritance issue, also present in GTK 3, rather
than a regression from Claude's gradient reset. No fix was applied during audit.

### R2 — P2: the spin-button fix has no behavior regression gate

Locations: `tools/check-gtk4.py:89` (horizontal spin fixture) and `:194–221`
(current assertions); equivalent rendering-only coverage in check-gtk3.py.

Both existing suites pass against the corrected theme. More importantly, both
also pass against disposable theme copies where **only Claude's two spin
background resets are removed**. This is a deliberate negative control, not a
hypothetical concern: the bad boxes return in the rendered images and the
suites still report PASS.

The GTK 4 fixture has one horizontal spin at its lower range boundary. It does
not assert the disabled button's image/background, include a vertical spin, or
cover all combined inactive/disabled/range-limit cases. Its standalone disabled
state is separate from backdrop. GTK 3 has wider rendered controls but likewise
no assertion that distinguishes these fixed/unfixed backgrounds.

Recommended follow-up: retain a GTK 3/4 matrix with both orientations, lower/
middle/upper values, fully disabled controls and combined backdrop+disabled
states. Assert the disabled buttons have no inherited gradient (or compare
relevant rendered regions) and prove the regression test fails when the reset
is removed. Also assert enabled mid-range controls and normal state are unchanged.

## What was verified about Claude's fix

- Read the exact GTK 3 diff: only two additions, one for horizontal and one for
  vertical `button:backdrop:disabled`. The GTK 4 equivalents are at lines
  **3313** and **3362** of gtk-4.0/gtk.css.
- The generic backdrop+disabled button rule supplies the unwanted gradient.
  Resetting `background-image` on the more specific spin selectors addresses
  that cause; `background-color` alone cannot remove the image layer.
- Ran a dedicated before/after rendering matrix on GTK 3.24.52 and GTK 4.24.1.
  Each tested horizontal/vertical spins at values 0, 50 and 100, plus disabled
  value-50 controls. Only the two reset declarations differed between variants.
- Normal-state fixed/unfixed screenshots are **pixel-identical**, on both
  toolkits. In backdrop, each toolkit changed exactly **16,666 pixels**, with
  the effects confined to the affected disabled/range-limited spin controls.
- Per-column combined horizontal/vertical differences: lower-bound 4,168;
  enabled middle 0; upper-bound 4,168; fully disabled 8,330 pixels, on both
  toolkits. Enabled mid-range controls stay unchanged.
- Current GTK 4 suite: ten renders pass, normal/dark variants, zero parser or
  worker errors. Current GTK 3 suite passes, including its selection/contrast
  and eight scale-1/scale-2 indicator cases.
- Deliberately reverted copies pass both existing suites too, establishing R2.
- All experiments used temporary themes/settings and private Unix-socket
  Broadway displays. No installed files, desktop settings, theme code, test
  code, release assets or AUR recipes were edited.

## Evidence and reproduction

Temporary matrix launcher: `/tmp/vapor-gtk4-review-probe.py`.
Temporary evidence: `/tmp/vapor-gtk4-review-5cr7yo0m/`:

- `gtk3-{fixed,unfixed}-{normal,backdrop}.png`
- `gtk4-{fixed,unfixed}-{normal,backdrop}.png`
- `probe3/unfixed/Vapor`, `probe4/unfixed/Vapor`: the negative-control copies.

Current-suite reruns:

```sh
python3 -I tools/check-gtk3.py
python3 -I tools/check-gtk4.py --output /tmp/vapor-gtk4-review-latest
```

Negative-control reruns (temporary copies must still exist):

```sh
python3 -I tools/check-gtk3.py --theme /tmp/vapor-gtk4-review-5cr7yo0m/probe3/unfixed/Vapor
python3 -I tools/check-gtk4.py --theme /tmp/vapor-gtk4-review-5cr7yo0m/probe4/unfixed/Vapor
```

These commands are scoped development checks, not installation commands.
The scratch launcher initially emitted test-only GTK 4 deprecation warnings
from get_style_context; changed that scratch call to the native add_css_class
API, then reran all eight matrix workers with no stderr. Production code was
not involved in that warning.

## Limits and next action

This review confirms Claude's spin fix, identifies the inherited checked-label
contrast issue and demonstrates missing regression coverage. It does not turn
the initial port into a complete release-ready GTK 4 theme. The already logged
keyboard-focus, open-menu, full-window/compositor, real HiDPI, accessibility,
reduced-motion/effects and application coverage gaps remain. The new matrix uses
synthetic backdrop state and normal-scale Cairo/Broadway rendering, not a live
Wayland session or a GPU performance benchmark.

Recommended next work: address R1 and add the failing-when-reverted regression
for R2, then continue the existing port checklist. Audit only: no theme fixes,
installation, commits, publication or scope expansion were performed.

---

# Historical pre-port assessment (unchanged)

# Audit: porting SteamOS Vapor to GTK 4

Date: **2026-10-30**, America/Phoenix. Auditor: **Codex (GPT-6)**.
Repository: `steamos-vapor-plasma-6.8`, branch `main`.
Audited commit: `4abe95d19366a437144bc2f469657563c2d86baa` (tagged-source recipe pin after v1.0.2).
Current release/package: **v1.0.2 / plasma6-themes-steamos-vapor-fixed 1.0.2-1**.

**Recommendation:** a genuine Vapor theme for ordinary GTK 4 applications is
feasible. Add a separate GTK 4 stylesheet and native widget tests, preserving
the existing GTK 3.24 theme. Do not describe a syntax-cleaned copy as a finished
port, or promise a complete libadwaita reskin. Most of the remaining effort is
widget/state coverage and visual validation, rather than changing color values.

This is a porting audit, not an implementation. All experimental CSS, programs
and screenshots were created under `/tmp`. This report is the only new project
file; no theme, package, application setting, installed file, release or AUR
submission was changed. No changes were committed or pushed.

## 1. Baseline and evidence

Installed audit environment:

| Component | Version |
| --- | --- |
| GTK 3 | 3.24.52 |
| GTK 4 | 4.24.1 |
| libadwaita | 1.10.0 |
| Python GObject bindings | 3.58.1 |
| Python Cairo bindings | 1.29.2 |
| Existing Breeze GTK comparison resources | 6.8.2 |

The implementation under review is `usr/share/themes/Vapor/gtk-3.24/gtk.css`
(**3,775 lines, 198,723 bytes**), with the GTK 3 chooser/import entry in
`gtk-3.0/gtk.css`. There is **no `gtk-4.0/` theme** in this release.
There are **110 PNG assets**, referenced by **176 CSS URLs**; all 110 distinct
image references resolve. The GTK 3 port and palette fixes are already released.

The source stylesheet SHA-256 is:

```text
3d8a27dd86692f050a3dcc3a0eef6cb38bdb19d41ee05881e3ddcf58b9ece653
```

Audit experiments:

| Check | Result | What it establishes |
| --- | --- | --- |
| Load unchanged Vapor CSS with GTK 4's parser | **42 errors** | Direct copying is not release-ready |
| Remove unsupported declarations and discard legacy radial gradients, in scratch CSS only | **0 parser events** | Syntax conversion is tractable; this deliberately loses effects |
| Load scratch theme by name from a temporary `themes/.../gtk-4.0/` directory | Pass, named-color marker found | GTK 4 discovers an independently installed theme |
| Enumerate actual GTK 4 widget children | Pass | Confirms changed entry, spin, scale, grouped-check and dropdown structures |
| Render a real GTK 4 Builder sample with scratch CSS | Pass, no render stderr | Basic Vapor appearance transfers, not complete state coverage |
| Initialize libadwaita with a selected custom GTK theme, without `GTK_THEME` | Theme changed to `Adwaita-empty` | A normal GTK theme alone is not a complete libadwaita solution |
| Verify production tree during experiments | Clean | No scratch port was added to the maintained theme |

The scratch render used a private GTK 4 Broadway server with its HTTP endpoint
on a Unix socket, temporary HOME/XDG config/cache/data/state/runtime paths,
an unavailable session bus, memory settings backend and Cairo renderer.
It rendered buttons/toggles, entry, grouped checks, spin button, scale, switch
and progress. It was inspected visually: Vapor surfaces and blue accents carry
over, but this is only a feasibility sample.

GTK's named-theme lookup was exercised using a process-local test theme, not
the user's desktop selection. The node probe emitted one Python deprecation
warning for `Gtk.CssProvider.load_named`; the render and libadwaita probe emitted
no stderr. Parser errors and that test-API warning are distinct results.

Scratch evidence (temporary, not required to use this report):

- `/tmp/vapor-gtk4-audit-4ub53usz/parse-events.json`: all 42 original errors.
- `summary.json`, `sanitization.json`, `sanitized-errors.json`: counts/transforms.
- `nodes.json`: live GTK 4 widget child trees.
- `sanitized-audit.ui`, `sanitized-audit.png`, `render-result.json`: feasibility render.
- `adw-result.json`: libadwaita initialization result.
- `/tmp/vapor-gtk4-audit-run.py`: isolated runtime experiment launcher.

## 2. Findings and required work

Priorities below concern a **future GTK 4 release**. They do not mean the
released GTK 3.24 theme has these parser failures.

### F1 — P1: the GTK 3 stylesheet cannot be installed unchanged as GTK 4

The 42 parser errors on GTK 4.24.1 break down as follows:

| Category | Occurrences | Examples / action |
| --- | --- | --- |
| GTK 3 widget style properties | 27 | Remove or replace `-GtkToolButton-icon-spacing`, indicator sizing, dialog spacing, tree-view lines, window dragging and scrollbar stepper settings |
| Removed icon-effect property | 4 | Replace `-gtk-icon-effect` with appropriate GTK 4 icon filters |
| Invalid legacy radial-gradient declarations | 11 | Rewrite `-gtk-gradient(radial, ...)` as standard radial gradients, with visual comparisons |
| **Total** | **42** | Must reach zero errors in the actual port |

The scratch sanitizer removed 31 unsupported property declarations and replaced
11 gradient declarations with `background-image: none`. It then parsed cleanly.
**That sanitizer is not the recommended port:** it discards attention/overscroll
effects and does not repair widget selectors or preserve every interaction.

The legacy radial gradients occur on source lines **297, 299, 1212, 2849, 2857,
2865, 2873, 2881, 2889, 2897 and 2905**. Icon-effect mappings should preserve
intent: dimming maps to opacity filtering and highlighting to brightness
filtering. Widget sizing moves to relevant CSS nodes' sizes, padding and spacing;
window dragging belongs to GTK 4 window-handle/headerbar behavior, not a theme
property. [GTK migration guidance](https://docs.gtk.org/gtk4/migrating-3to4.html)

The existing named colors, `alpha()`, `shade()`, `mix()`, ordinary linear
gradients and `-gtk-scaled()` image pairs did not produce parser errors in this
test. They need not all be replaced merely because their syntax looks old.
GTK 4 still documents scaled image pairs and icon sources/filters.
[GTK 4 image/property reference](https://docs.gtk.org/gtk4/css-properties.html)

### F2 — P1: widget structures require a deliberate selector audit

A parser accepts selectors for nonexistent nodes without proving they match.
The current theme includes GTK 3 structures and historical widget-type selectors.
The following mapping is for **the inspected GTK 4.24.1**, not a promise that all
GTK 4 minor versions have identical internal layouts.

| Area | Current assumption / porting concern | GTK 4 target / required check |
| --- | --- | --- |
| Entry | Broad entry styling and selected-text rules | `entry > text`; cover caret, selection, icons, progress, disabled and focus states |
| Spin button | Rules target a child `entry` | Child is `text`, beside `.up`/`.down` buttons; avoid missing text styling or doubled borders |
| Radio controls | `radiobutton` root selectors | Grouped `checkbutton` with a `radio` child; retarget all state/image rules |
| Dropdown | Combo-box-era selectors | Add `dropdown` button/popover/list coverage, including selected items and keyboard navigation |
| Menus | `menu`, `menuitem`, `menubar`, `modelbutton.flat` | Add GTK 4 menu/popover content styling; current menu items use `button.model` |
| List/table views | Heavy `treeview` styling | Cover `listview`, `gridview`, `columnview`, rows/cells/headers and rubberband selection |
| Headerbar | Older button/titlebar relationships | Account for `windowhandle`, boxes and `windowcontrols`; verify close/minimize/maximize placement and states |
| Scales | GTK 3 hierarchy assumptions | Live GTK 4 scale has trough directly below scale; preserve geometry during focus, fine-tuning and RTL |
| Popovers | Outer `popover.background` rules | Check the inner `contents`/arrow structure; styling only the outer container can miss the visible surface |
| Notebook, tooltips, scrolling, calendar | Partial apparent similarity | Verify their actual nodes and rendered states, not just parser acceptance |

Actual node enumeration confirmed `entry > text`, `spinbutton > text`, grouped
`checkbutton > radio`, `scale > trough`, and the dropdown button/popover structure.
The remaining rows also use installed GTK 4 GIR documentation and official widget
references. Some legacy widgets remain available but deprecated: do not assume
all GTK 3-era class names disappeared, or treat their coverage as coverage of
the modern replacements.

References: [Entry](https://docs.gtk.org/gtk4/class.Entry.html),
[SpinButton](https://docs.gtk.org/gtk4/class.SpinButton.html),
[CheckButton](https://docs.gtk.org/gtk4/class.CheckButton.html),
[PopoverMenu](https://docs.gtk.org/gtk4/class.PopoverMenu.html),
[ListView](https://docs.gtk.org/gtk4/class.ListView.html),
[HeaderBar](https://docs.gtk.org/gtk4/class.HeaderBar.html),
[Popover](https://docs.gtk.org/gtk4/class.Popover.html).

### F3 — P1: preserve the corrected Vapor selection palette and contrast

Use the released theme and `Vapor.colors` as the visual baseline:

| Purpose | Required baseline |
| --- | --- |
| Window/button surface | `#24272c` |
| Entry/view surface | `#151c23` |
| Ordinary foreground | `#eff0f1` |
| Selection background | **`#569fcc`**, RGB 86,159,204 |
| Full-strength selection text | **`#1f1f26`**, RGB 31,31,38 |
| Dimmed selection text | **`#eff0f1`**, on half-alpha selection blue over the view |

Calculated sRGB contrast is approximately **5.64:1** for the full-strength pair,
and **6.12:1** for light text on the half-alpha blue composited over `#151c23`.
Dark text on that dimmed background was already fixed in Claude's GTK 3 review;
do not reintroduce it during the GTK 4 port. Actual compositing backgrounds in
GTK 4 must be verified rather than assumed.

Some inactive activatable rows retain full-strength selection and therefore
need the dark text; dimmed entry/text/tree selections need the light text.
Descendant labels must inherit the correct selected foreground. Require at
least 4.5:1 for normal-size selection text in both cases, as the current GTK 3
regression does. Verify keyboard focus visibility separately.

Keep the Vapor-specific palette as the initial scope. The current theme does
not dynamically follow arbitrary KDE schemes. Adopting GTK 4 CSS variables is
an optional implementation choice after choosing a minimum GTK 4 version; it
must not silently change the palette or introduce an undeclared version floor.

### F4 — P2: the corrected artwork can be reused, but needs GTK 4 state tests

All 110 referenced PNGs exist, including the Vapor-blue check/radio updates and
normal/@2 pairs. Reuse suitable files through relative paths shared with GTK 3.
The parser accepted their scaled image expressions. Geometry/alpha need not be
redesigned to start the port.

However, syntactically accepted images may match different nodes or be affected
by GTK 4 icon rendering. Test check/radio off/on/mixed, hover, pressed, disabled,
backdrop and grouped states, including menu items, at normal and double scale.
Validate both the image references and the pixels actually rendered. Do not
remove an asset just because GTK 4 does not use it: GTK 3 still shares the folder.
SVG indicators are a possible later optimization, not required for this port.

### F5 — P1 scope boundary: GTK 4 support is not full libadwaita theming

A separate, isolated probe set `gtk-theme-name` to the scratch Vapor theme,
then initialized **libadwaita 1.10.0** without a `GTK_THEME` override. The name
changed from `VaporAuditGtk4` to **`Adwaita-empty`**. This agrees with the
library's style manager, which establishes its own stylesheet providers.
[libadwaita 1.10 source](https://github.com/GNOME/libadwaita/blob/1.10.0/src/adw-style-manager.c)

A successful ordinary GTK 4 port therefore must not be advertised as applying
Vapor unchanged to every GNOME/libadwaita app. Document libadwaita's existing
system dark/accent integration separately. Its public accent support is not a
guarantee of Vapor's exact custom color in every desktop/application context.
[libadwaita appearance documentation](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.10/styles-and-appearance.html)

Do not ship a global `GTK_THEME` export, inject a universal user gtk.css, patch
application resources, or force libadwaita overrides as part of the theme's
installation. Full libadwaita restyling would be a separate, broader maintenance
commitment requiring explicit scope and per-version testing. No complete
libadwaita application rendering was tested in this audit.

### F6 — P2: add a GTK 4-native rendering harness

`tools/check-gtk3.py` relies on GTK 3 facilities such as `Gtk.OffscreenWindow`,
`Gtk.WidgetPath`, `Gtk.RadioButton` and `Gtk.ModelButton`, which the GTK 4
bindings do not provide. It cannot be made into a GTK 4 checker by changing only
the import version. Some drawing helpers still exist; the larger fixture and
style-query assumptions are the problem.

Create an independent GTK 4 sample using real widgets, real child nodes and
snapshot/render output. The installed `gtk4-builder-tool render` successfully
rendered the scratch fixture on the private display; a custom harness can also
use `Gtk.WidgetPaintable` and GTK/GSK snapshot rendering. Prefer live discovery
and a staged-theme marker over deprecated named-provider queries: the audit's
`load_named` probe works today but already warns on 4.24.1.
[WidgetPaintable](https://docs.gtk.org/gtk4/class.WidgetPaintable.html)

Keep GTK 3 regressions intact and run both toolkits in separate processes.
A passing parser, one screenshot, or synthetic state alone is insufficient
proof of complete behavior.

### F7 — P2: deployment and packaging are straightforward, but need real checks

Recommended runtime layout:

```text
usr/share/themes/Vapor/
  gtk-3.0/gtk.css       # existing GTK 3 entry
  gtk-3.24/gtk.css      # existing GTK 3 implementation
  gtk-4.0/gtk.css       # new, independent GTK 4 implementation
  assets/              # shared artwork where appropriate
```

GTK 4 searches GTK 4 versioned directories; it does not use the GTK 3 stylesheet
as its version fallback. An explicit dark entry may import the same dark Vapor
implementation; alternatively verify the named loader's normal/dark fallback.
Do not assume a file existing under `gtk-3.0` supplies GTK 4 styling.
[GTK 4 theme lookup](https://docs.gtk.org/gtk4/class.CssProvider.html)

The current `aur/PKGBUILD` copies `usr/`, so a new GTK 4 directory will be included
without a new install script. A later release still needs a new version,
immutable source/tag/checksum, generated .SRCINFO, package inspection and an
explicitly requested GitHub/AUR publication. Consider GTK 4 as an optional
consumer; shipping CSS alone does not justify forcing GTK 4/libadwaita onto
users who only need the Plasma/GTK 3 theme. Test dependencies belong in the
check/development environment. The port does not require importing Breeze GTK.

Verify selection through Plasma's GTK settings and a real GTK 4 app after an
authorized install. This audit did not validate KDE settings propagation or
whether every application honors the selection.

Flatpak is another separate deployment boundary. A host `/usr/share/themes`
installation is not automatically visible as the same filesystem inside an
application sandbox. Do not promise Flatpak coverage from the AUR package or
assume the existing GTK 3 extension mechanism proves GTK 4 runtime support.
[Flatpak desktop integration](https://docs.flatpak.org/en/latest/desktop-integration.html#theming)

### F8 — P2: preserve accessibility and measure renderer-specific behavior

GTK 4's renderer and native controls differ from GTK 3. The Cairo/Broadway
scratch screenshot is a feasibility check, not a GPU or session benchmark.
Neither lower nor higher performance has been established.

Avoid adopting new infinite animations, broad expensive effects or blanket CSS
resets without measuring them. Preserve a visible keyboard focus indicator,
respect reduced-motion/high-contrast preferences where supported, and test
keyboard navigation, text scaling, clipped controls and disabled-state clarity.
Retain focus/drag geometry stability; do not undo the reviewed GTK 3 decision
that prevents slider shrinkage during fine-tuning.

## 3. Recommended implementation order

1. **Set scope and baseline.** Target ordinary GTK 4 apps first, initially on
   the measured 4.24.1 environment. Choose/document any lower supported version
   before using newer CSS features. Keep full libadwaita reskinning out of the
   initial promise. Capture v1.0.2 GTK 3 controls/colors as references.
2. **Add an isolated GTK 4 fixture first.** Include a named-theme discovery
   marker, parser/error capture, asset checks and real screenshot output.
   Start with selected text/rows and ordinary entry/button contrast tests.
3. **Create `gtk-4.0/gtk.css`.** Carry over palette and supported effects,
   replace the unsupported properties/gradients and map basic control nodes.
   Keep the GTK 3 stylesheet and its tests unchanged.
4. **Complete widget coverage.** Grouped checks, spin controls, dropdowns,
   popover menus, list/grid/column views, headers/window controls, scrolling,
   notebooks, tooltips, progress, keyboard focus and disabled/error states.
5. **Verify state/scale parity.** Compare the intended look and geometry;
   validate contrast, dark selection, inactive rows, RTL, large text,
   motion/contrast preferences and real HiDPI behavior. Do not demand identical
   GTK 3/4 pixels where toolkit layout changed; document deliberate differences.
6. **Test a real installed session only when authorized.** Native GTK 4 app,
   actual Plasma theme selection, Wayland focus/backdrop, popovers and monitor
   scales. Record ordinary GTK vs libadwaita vs sandboxed-app results separately.
7. **Package and publish separately.** Inspect the built package, run GTK 3 and
   GTK 4 regressions, bump version and source hash, then release/update AUR only
   after a user request. Do not overwrite v1.0.2 assets or its tag.

This is a moderate-to-substantial theme feature with a manageable syntax phase.
The largest uncertainties are coverage of modern widgets, focus/backdrop
behavior, high-DPI rendering and the application support boundary. No reliable
completion-time estimate is justified by a parser-only conversion.

## 4. Acceptance criteria for claiming GTK 4 support

- Zero CSS parse errors and missing assets for all advertised variants.
- A staged named-theme test proves the fixture used Vapor, not a system theme.
- Selection colors and active/inactive text contrast match the corrected Vapor
  palette; focus remains visible and descendant labels stay readable.
- Checked/radio/mixed/menu indicators render at both scales; no stale blue,
  invisible indicators, clipped glyphs or geometry jumps.
- Modern list/column/dropdown/menu/header controls are tested, not inferred
  from deprecated GTK 4 widgets or CSS parsing.
- GTK 3.24 tests still pass and the existing GTK 3 look is unchanged.
- Real Wayland/HiDPI checks and tested application/toolkit versions are recorded.
- README accurately distinguishes native GTK 4 theme support from libadwaita
  and Flatpak coverage; installation remains appearance-only and user-selected.

## 5. Reproducing the parser finding

From this repository root with GTK 4 and Python GObject bindings installed:

```sh
python3 -I - <<'PY'
import collections
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
errors = []
def on_error(_provider, section, error):
    errors.append((section.get_start_location().lines + 1, error.message))
provider = Gtk.CssProvider()
provider.connect('parsing-error', on_error)
provider.load_from_path('usr/share/themes/Vapor/gtk-3.24/gtk.css')
print('GTK', Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version())
print('Parser events:', len(errors))
for message, count in collections.Counter(message for _, message in errors).items():
    print(count, message)
PY
```

Expected at the audited source hash and GTK 4.24.1: **42 events**, with the
breakdown above. This loads CSS as data and changes no installed configuration.
Later GTK/source versions may produce different counts.

## 6. Limits and final decision

Confirmed: missing GTK 4 runtime payload, exact parser blockers, reusable image
references/palette, named loading, several actual widget structures, a simple
scratch rendering and libadwaita's theme reset on initialization.

Not confirmed: a complete port, production GTK 4 rendering parity, live Plasma
selection propagation, a complete libadwaita application's visuals, Flatpak
availability, real GPU performance, high contrast, accessibility interactions,
full-window scale 2/fractional scaling, older GTK 4 versions or a clean Arch build.

**Proceed with a separate Vapor GTK 4 theme and native regression suite when
implementation is authorized.** Keep the current GTK 3 work intact and retain
the precise selection/backdrop contrast fixes already reviewed.
