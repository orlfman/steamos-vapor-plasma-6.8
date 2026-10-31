# VGUI2 Classic port plan: GTK 3, GTK 4 and libadwaita

Date: **2026-10-30**, America/Phoenix. Agent: Codex (GPT-6).
Status: **GTK 3/4 audited and native libadwaita color profile implemented/tested, released in 1.1.0**.
Shared profile activation is implemented and released in **1.1.0**.
Findings and measured feasibility: [vgui2-audit.md](vgui2-audit.md).
Baseline: Vapor 1.0.4 / repository `e626869` on Plasma 6.8.2.

| Stage | Current status |
| --- | --- |
| 1: identity/palette/reference | VGUI2Classic identity, audited palette and fresh Qt Windows reference implemented |
| 2: harness | Family-aware GTK 3/4, Widget Factory and Adw checks; 23 GTK 3/32 GTK 4/25 Adw VGUI mutations; actual variant markers and audit controls |
| 3: GTK 3.24 | Independent stylesheet, six SVG glyphs, normal/dark entries; follow-up message/selection/focus/arrow fixes verified; standard checks and Meld 3.24.1 pass |
| 4: plain GTK 4 | Independent GTK 4 entries/style audited; frame/field/separator/expander fixes, actual variants, selection, native/Widget Factory and scale-2 tests pass |
| 5: native Adw profile | Audited 28-role palette; readable checked ink/input focus and native semantic outlines; 34 surface cases, 12×50 control checks, 25 mutations and deeper plain-GTK coexistence pass |
| 6: shared activation | Implemented; schema-1 compatibility, transactional swaps, persistent disable and 38 recovery/migration checks |
| 7: real apps/displays/performance | Private Meld/GTK Widget Factory, Adw demo and FFmpeg Converter startup pass; integer GTK 4 scale 2 covered; live fractional scaling/keyboard/accessibility/performance pending |
| 8: packaging/release | Standard installation and 1.1.0 / AUR 1.1.0-1 |

Implementation details/results: [VGUI2-GTK3.md](VGUI2-GTK3.md), [VGUI2-GTK4.md](VGUI2-GTK4.md),
[VGUI2-LIBADWAITA.md](VGUI2-LIBADWAITA.md),
[portable evidence](docs/audits/vgui2-gtk3-validation.json), and
[gtk4port.md](gtk4port.md), sections 22–27. The roadmap below retains the full scope.

## Intended result

Deliver a separate **VGUI2 Classic** theme family that leaves Vapor available:

| Target | First supported result |
| --- | --- |
| GTK 3.24 | Olive/gold colors with traditional square/beveled controls and complete state coverage |
| Plain GTK 4, initially tested on 4.24.1 | Same visual language, with GTK 4-specific nodes and states |
| Native libadwaita 1.10+ on GTK 4.24+ | Matching dark olive/gold color profile, readable selections/focus, native Adwaita geometry |
| Activation | A shared manager chooses Vapor or VGUI2 from the selected GTK theme; disable remains persistent |

Do not add GTK 2, change Qt's selected widget style, force Union, replace
decorations/cursors/icons, alter app preferences or modify unrelated system
behavior. Flatpak and a full classic Adwaita geometry reskin are later work.
Dark native colors remain conditional on normal contrast; preserve light/high
contrast rather than forcing every app into the olive palette.

## Stage 1 — Establish identity, palette and reference controls

Use **VGUI2Classic** as the canonical GTK folder/selection name and **vgui2** as
the shared profile ID. Display it as VGUI2 Classic where metadata is supported.
Keep the existing VGUI/VGUIUnion KDE schemes and Vapor assets unchanged.

Proposed source layout:

```text
usr/share/themes/VGUI2Classic/
  gtk-3.0/gtk.css          # standard entry importing the maintained GTK 3.24 CSS
  gtk-3.24/gtk.css
  gtk-3.24/gtk-dark.css    # explicit same-palette dark entry, if used by loader
  gtk-4.0/gtk.css
  gtk-4.0/gtk-dark.css
  assets/                 # independently reviewed indicators/artwork
libadwaita/vgui2.css
```

Verify discovery and normal/dark fallback using the actual named loader.
Add clear chooser metadata where supported; do not assume a folder alone
proves the theme was selected. A named `VGUI2Classic-dark` alias is optional and
must not be advertised unless actually packaged and tested.

Start with these role decisions, recording differences from the Qt reference:

| Role | Starting value / policy |
| --- | --- |
| Window, header, ordinary button | `#4d5845` |
| Content and primary sidebar | `#3f4638` |
| Darker secondary surface | `#282f21`, subject to visual review |
| Ordinary text | `#fcfcfc` |
| Solid selected/suggested fill | Original gold `#958831` |
| Text on solid gold | `#181810`, matching the readable Union selection foreground |
| Dimmed selections | Light text on the actual dimmed background; distinguish full-strength inactive rows |
| Links and visible focus | Separate brighter roles; do not copy the failing classic link/focus values |
| Adw standalone accent trial | `#ffffe0`: 3.19:1 focus in the audit fixture; validate all relevant adjacent surfaces |
| Adw raised/card trial | `#56604e`: derived proposal, not an existing Qt palette value |
| Semantic states | GTK: review VGUI semantic text colors and paired fills; Adw: retain upstream semantic treatment initially |

Create a fresh reference image of Qt controls under VGUI2 Classic and compare
the proposed GTK controls to it. Retain system fonts, font-size preferences and
usable hit targets. Decide bevel light/shadow roles and square-corner treatment
explicitly instead of mechanically recoloring every Vapor literal.
The solid-gold/dark-text pair has limited margin above 4.5:1; test the darkest
gradient area under text instead of relying on an average button color.

**Completion:** role/specification data exists, contrast calculations pass,
expected readability differences are documented and toolkit names resolve.

## Stage 2 — Make the existing harness support theme families

Before relying on `--theme`, remove its hidden dependency on Vapor expectations.
Use an explicit family specification for theme names, source roots, KDE role
mapping, approved foreground overrides and Adw profile/expected variables.
Keep Vapor as the default invocation for compatibility.

Update GTK 3/4 checkers, shared behavior tests, Widget Factory driver, artwork
checks and Adw tests. Preserve the existing label inheritance, disabled/pressed
guards, spin-button gradients, surface pixels, focus background sampling and
appearance/geometry checks. Compare unrounded contrast values at the gate.
Expected values must be independently anchored in the family specification and
the audited palette; a bulk replacement script is not its own oracle.

Add deliberate bad VGUI copies that fail for the intended reason:

- Vapor-blue controls/artwork or a wrong olive surface despite correct variables.
- Light text on solid gold; dark text incorrectly applied to dimmed selections.
- A checked/pressed child label that loses the selected foreground.
- Reintroduced spin gradients, missing dark/high-contrast guards, missing import
  or invalid CSS.
- Derived gold focus and Union-gold focus that reproduced 2.38:1 and 2.63:1.
- A missing or mismatched expected family/discovery result.

**Completion:** the original Vapor suite stays green and each new negative
control fails its specific VGUI assertion. No automatic skip or weakened gate.

## Stage 3 — Implement and verify GTK 3.24

Use the maintained Vapor GTK 3.24 branch as a compatibility reference for the
independent VGUI2Classic family. Keep the standard gtk-3.0
entry. Replace every palette-dependent surface, gradient, border, shadow,
selection, foreground and indicator deliberately. Do not import all of Vapor
at runtime and depend on later overrides to conceal it.

Implement normal, hover, pressed, checked, mixed, disabled and backdrop states
for entries/text selections, rows/tree views, buttons, checks/radios, switches,
sliders, horizontal/vertical spins, tabs, menus, tooltips, toolbars/headers,
sidebars, scrollbars, progress and semantic messages. Preserve the established
inactive-label/spin corrections while giving controls their classic treatment.

Prefer maintainable CSS/SVG geometry where practical. If retaining PNGs, review
all 110 referenced assets, including antialiasing, non-exact blue tints, neutral
edges, selected/unselected/mixed glyphs and 1x/2x scaling. Retain provenance and
licensing for copied assets. Avoid unused copies and new missing references.

**Completion:** parser/URL/artwork checks, discovery, native renders, selection
and actual label contrast pass for VGUI2; unchanged Vapor still passes. Review
at least one real GTK 3 app and popup/file-dialog paths, using private fixtures
for automation and avoiding actions that change the user's files/settings.

## Stage 4 — Implement plain GTK 4 independently

Start from the maintained GTK 4 branch and transfer the approved VGUI visual
rules, adapting nodes/properties using GTK 4 documentation. Include an explicit
dark entry, correct GTK 4 icon styling, grouped check buttons, dropdowns,
popover menus, list/column views and visible keyboard focus. Do not copy GTK 3
widget properties or obsolete nodes blindly.

Run native and behavior tests plus all installed Widget Factory pages in
normal/dark requests, synthetic backdrop and RTL. Check actual theme discovery,
olive/gold surfaces, independent foreground states, nonblank rendering and
layout at the tested scales. Use a plain GTK app as separate evidence from
libadwaita applications.

**Completion:** VGUI2 GTK 4 stages and mutations pass without loosening Vapor
checks; real-app screenshots show the agreed classic GTK treatment.

## Stage 5 — Add the native libadwaita color profile

**Implemented and tested:** [guide and boundary](VGUI2-LIBADWAITA.md),
[portable results](docs/audits/vgui2-libadwaita-validation.json). The wider matrix
found 2.95:1 native focus on cards; guarded 65% button focus coverage raises the
lowest tested suggested-button surface to 3.84:1 while retaining native geometry. VGUI2 now has
34 cases; Vapor retains its original 22. The requirements below remain the
design record; shared automatic activation is completed in stage 6 below.

The follow-up audit extends coverage to native controls and corrects checked
text/focus, input rings, compound semantic inheritance and a plain-GTK focus
leak. Three private coverage/ink controls and a local plain-theme focus bridge
retain native fills/shapes and semantic roles. See [audit evidence](docs/audits/vgui2-libadwaita-audit.json).

Add `libadwaita/vgui2.css` under the existing dark/normal-contrast guard. Start
with the audit's 27 mapped surface/foreground roles and the separate pale
standalone accent that resolved the measured focus failure. Treat that color
as a candidate, not a guarantee for every widget/background.

Retain Adwaita structure, geometry, semantic classes, light/high-contrast
fallback and the user's appearance preference. Do not flatten shapes, import
the full GTK stylesheet, override global accessibility helper opacities or
replace the system accent API to make a screenshot match.

Run the expanded 22-case native matrix for both profiles, including actual
window/header/card/view/sidebar/dialog/popover surfaces, focus against adjacent
pixels, opaque text pairs, dark/light transitions, RTL, backdrop and scale 2.
Check focus on additional cards/sidebar/popover backgrounds, not just the main
window where the trial measured 3.19:1. Validate themed widget colors separately
from apps' custom graphs and unchanged system-accent API output.
If a focus surface fails, adjust its painted contrast within the appearance
guard and re-test; retain the gate and native geometry.

Run plain GTK/Widget Factory coexistence for each matching theme/profile and
for supported switching paths. Test the new profile's mutations independently.

**Completion:** profile and coexistence gates pass; document that Adw matches
the palette while retaining native shapes. No claim of full classic Adw skinning.

## Stage 6 — Extend activation and migrate existing installations safely

**Implemented in 1.1.0.** The requirements below are retained as the design record.

Retain `vapor-libadwaita` and the current autostart entry as compatible entry
points. Extend the manager with explicit profile selection, for example
`enable --theme vgui2`, plus a whitelist mapping the packaged GTK names to
Vapor/VGUI2 profiles. Preserve legacy enable behavior and diagnostic `--profile`.
Use one shared decision path for selected profile, runtime checks and execution.

- Keep one managed import, copied profile and original backup. Preserve existing
  managed filenames/markers unless a separately tested migration requires more.
- Recognize old schema-1 metadata as the legacy Vapor profile; validate any new
  profile ID and reject unknown values. Preserve the original backup and edits
  during a digest-checked, transactional profile swap.
- Keep the existing shared persistent disable preference. Changing theme must
  never clear it. Enable explicitly re-enables the layer.
- Preserve KDE colors/imports, external CSS regeneration, permissions, dry runs,
  collision/symlink/read-only refusals, local-profile edit detection and rollback.
- Keep theme detection based on actual GTK selection, GTK 4 first/GTK 3 fallback.
  Do not force a GTK choice because the Plasma global theme or Union changed.
- Keep the once-per-login behavior and immediate `auto` command; add no watcher
  or second competing login/helper process.

Add migration tests for existing enabled/disabled/missing-import/edited setups,
Vapor -> VGUI2 -> Vapor -> another theme, legacy state, backup identity,
invalid profile IDs, failed switches and upgrade/reapply. Include no-existing-
CSS and originally empty CSS cases. Test the packaged helper, not only source.

**Completion:** all current 28 recovery tests remain valid or are extended with
explicitly documented expectations; new profile/migration tests pass and prove
no duplicate import, lost backup or surprise re-enable.

## Stage 7 — Real applications, displays and performance

Record separate versions/results for a GTK 3 app, plain GTK 4 Widget Factory,
and native Adw apps such as Mission Center/FFmpeg Converter where appropriate.
Verify keyboard navigation, readable selections, dialog/popover placement,
sidebar hierarchy, scrolling, mixed/disabled states, RTL and large text.

Repeat live checks at 100%, integer HiDPI and the user's 4K/175% configuration.
Vapor's previous successful display/app screenshots do not validate VGUI2.
Document focus/semantic differences and application-defined colors accurately.

Compare startup, idle CPU/RSS, scrolling/resizing and rendering against Vapor
and upstream Adwaita using the same app/content/display setup. Use repeated
measurements; report limits and any regressions. Static classic bevels should
avoid elaborate effects, but that is a design direction, not a speed claim.
Do not run video conversions or destructive app actions merely to test a theme.

**Completion:** no observed regression in the tested scenarios; actual manual
and measured results are distinguished from automated/headless coverage.

## Stage 8 — Package, document and release the tested family

Extend the shared stager's explicit profile/document lists and staging tests.
The new GTK folder will already be copied through `usr`. Keep the existing
runtime dependencies unless implementation establishes another requirement.
Include the family guide, contrast decisions, real screenshots and clear
selection/automatic-switch/disable/rollback instructions. Keep the current
published release untouched while the port is in progress.

Run both families' full standard suites and negative controls, build an Arch
package, inspect all assets/metadata and smoke-test the packaged helper with a
temporary config. Confirm build/install transactions do not change homes.
Then use a new version/tag, verified archive checksum, generated .SRCINFO and
the normal GitHub/AUR workflow. Flatpak support requires its own passing tests
before inclusion in release claims.

**Completion:** both families install and switch cleanly; documentation and
package contents agree; existing Vapor users retain their working appearance.

## Effort and first implementation step

This is a moderate-to-large theme extension. The color-only Adw file is the
smallest part; classic GTK finishing, adapting the tests and safe shared-profile
migration carry most of the work. The audit's passing private profile reduces
feasibility uncertainty without replacing those tasks.

The GTK 3/4 and native Adw milestones now cover stages 1–5, including relevant
test work. Stage 6 and release packaging are now complete in **1.1.0**, including
shared selection and safe migration tests. Broader live display, accessibility
and performance validation remain open; existing GTK theme choices are preserved.
