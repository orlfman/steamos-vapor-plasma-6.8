# VGUI2 Classic: GTK 3, GTK 4 and libadwaita port audit

**Implementation follow-up:** the user subsequently requested starting GTK 3.
An initial VGUI2Classic GTK 3.24 theme and its tests are now implemented;
see [VGUI2-GTK3.md](VGUI2-GTK3.md) and [the status table](vgui2-plan.md).
The findings below preserve the pre-port investigation. GTK 4, VGUI2 Adw and
shared profile switching remain future work.

Date: **2026-10-30**, America/Phoenix. Agent: Codex (GPT-6).
Audited base: `e626869`, clean before investigation. Scope: feasibility and
implementation requirements; no production theme or live settings changed.
Implementation roadmap: [vgui2-plan.md](vgui2-plan.md).

**Result: feasible, with separate GTK themes and a libadwaita color profile.**
GTK 3/4 can reproduce the olive/gold palette and traditional control treatment.
For the first libadwaita milestone, match colors while retaining native widget
shapes and layout. A complete classic Adwaita reskin would be a separate project.
This audit does not claim that a VGUI2 GTK theme already exists or is supported.

## Evidence and supported starting point

Installed environment: Plasma **6.8.2**, Qt **6.12.0**, GTK **3.24.52**,
GTK **4.24.1**, libadwaita **1.10.0**. These are the local investigation targets;
support for other versions needs its own checks.

| Existing source | Finding |
| --- | --- |
| `usr/share/color-schemes/VGUI.colors` | Authoritative classic olive/gold palette; display name VGUI2 Classic |
| `usr/share/color-schemes/VGUIUnion.colors` | Same main surfaces; dark selected text and brighter focus treatment |
| `usr/share/plasma/look-and-feel/com.valve.vgui.desktop/contents/defaults` | Requests Qt Windows widgets, Plastik decoration, VGUI colors, default Plasma style; does not select a GTK theme |
| `usr/share/plasma/look-and-feel/com.valve.vgui.desktop/contents/previews/preview.png` | Historical visual reference for square/beveled olive controls; not a fresh Plasma 6.8.2 acceptance capture |
| `usr/share/themes/` | Contains Vapor only; no VGUI2 GTK family |
| `libadwaita/` | Contains Vapor only; no VGUI2 color profile |

The maintained Vapor GTK 3 stylesheet has **3,784 lines**; GTK 4 has **3,892**.
Each contains **33 distinct literal hex colors**, **58 gradient expressions**
and **176 URL references to 110 distinct assets**. All 110 assets are PNGs;
30 contain a nontransparent pixel of the exact Vapor selection blue. Other
antialiased/tinted pixels and neutral artwork also need review.

This is a new sibling theme using the existing engineering as a starting point,
rather than conversion of an existing VGUI GTK stylesheet. Changing only the
named accent leaves hardcoded blue-grey surfaces, gradients and artwork behind.

## VGUI-A1 — P1: define the visual target and independent theme identity

The KDE reference combines a color scheme with Qt's Windows widget style.
GTK cannot consume that QStyle or the Plastik window decoration as a widget
stylesheet. The GTK port needs its own controls, borders, indicators and states.

Recommended identity: folder/GTK theme name **VGUI2Classic**, display name
**VGUI2 Classic**, internal profile ID **vgui2**. These are proposed names, not
installed entries. Keep Vapor and the existing KDE VGUI/Union definitions intact.
Keep Union user-selected; it is a Qt style choice, not a second GTK engine.

Use olive windows, darker olive content, gold selection, restrained square
corners and raised/sunken edges in plain GTK. Retain normal system fonts,
text sizing and usable control targets. Review against a fresh Qt reference
before claiming a close match; the old bundled preview alone is insufficient.

## VGUI-A2 — P1: a literal palette copy fails selection, link and focus checks

The following are sRGB calculations on the actual scheme values. They are
palette measurements, not whole-application accessibility certification.

| Pair | Foreground / background | Contrast |
| --- | --- | --- |
| Classic selected text | `#fcfcfc` / `#958831` | **3.503:1** |
| Recommended selected text, from Union | `#181810` / `#958831` | **4.965:1** |
| Ordinary window text | `#fcfcfc` / `#4d5845` | **7.317:1** |
| Ordinary content text | `#fcfcfc` / `#3f4638` | **9.545:1** |
| Light text on half-strength inactive gold over content | `#fcfcfc` / `#6a6734` | **5.682:1** |
| Dark text on that dimmed background | `#181810` / `#6a6734` | **3.061:1** |
| Original link text on windows / content | `#b0b07b` / olive surfaces | **3.340 / 4.356:1** |
| Original solid focus gold on windows / content | `#958831` / olive surfaces | **2.089 / 2.725:1** |
| Union solid focus gold on windows | `#f0e078` / `#4d5845` | **5.590:1** |

Adopt the project's 4.5:1 normal enabled-text and 3:1 focus/component gates,
guided by [text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
and [non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
Use unrounded values for decisions and rounded values for presentation.
Disabled controls and inactive-window enabled controls must be distinguished.

Recommended policy: keep the original gold fill, use dark text on opaque gold,
and use light text where selection backgrounds are dimmed. Give ordinary links
and focus their own brighter roles. Do not silently modify the existing Qt
classic scheme; document the GTK readability differences from its light text.

### Disposable native libadwaita experiment

Adapted a private copy of `tools/check-libadwaita.py` to VGUI expected colors.
Only repository lookup, palette expectations and the corresponding hardcoded
accent RGB expectations changed. Existing surface-pixel, contrast, geometry,
semantic-color, appearance and scale checks remained enabled. No assertions or
thresholds were removed. Every application used private HOME/XDG/display state.

The candidate maps window/header/dialog/popover to `#4d5845`, content/primary
sidebar to `#3f4638`, secondary sidebar to `#282f21`, text to `#fcfcfc`, accent
fill to `#958831` and its text to `#181810`. The raised/card trial color
`#56604e` is approximately 5% white over the window; it is a design proposal,
not an existing VGUI scheme value.

| Standalone accent treatment | Actual focus contrast on RGB 77,88,69 | Result |
| --- | --- | --- |
| Adwaita-derived standalone gold | **2.38:1** | Focus gate fails after preceding fixtures pass |
| Explicit Union focus gold `#f0e078` | **2.63:1** | Focus-only case fails |
| Brighter gold `#fff2c2` | **2.98:1** | Focus gate still fails |
| Pale gold `#ffffe0` | **3.19:1** | All **22** adapted native cases pass |

In the passing trial, suggested-action text measures **4.97:1** and selected-row
text **5.53:1**. The checks also retain baseline geometry, original semantic
colors and identical light/high-contrast fallback images, including scale 2 and
dark/light transitions. The gold control fill never needs to become pale yellow;
`--accent-color` supplies the separate standalone/focus treatment.

This establishes a viable color-profile direction, not a finished port. The
private fixture still uses its existing synthetic theme setup; it does not test
VGUI2 theme discovery, plain GTK coexistence, real application interactions or
every possible focus background. The proposed pale color needs those checks.

## VGUI-A3 — P1: activation must support profiles without stacking overlays

`tools/vapor-libadwaita` currently recognizes Vapor/Vapor-dark in both its early
runtime decision and its managed operation. Its default source/profile paths,
managed import, copied CSS, state, backup and persistent-disable preference are
Vapor-specific. Merely shipping `libadwaita/vgui2.css` does not select it.

With the current helper, selecting a proposed VGUI2 GTK name makes `auto` remove
the managed overlay. Manually enabling an alternate `--profile` does not add
automatic VGUI2 selection; the next login still follows the Vapor-only rules.

Extend the existing manager with an explicit whitelist of GTK names/profile
IDs. Maintain **one** managed import and original backup, switching the owned
profile atomically after validating its current digest. Read existing 1.0.4
metadata as Vapor, preserve its backup and edits, and retain legacy commands.
The existing persistent off preference should apply to the shared layer, so a
theme switch cannot undo an explicit disable. Avoid a second competing helper
or login entry. Test migrations and failed switches before enabling automation.

Plasma global themes and GTK themes remain separate selections. The current
global VGUI defaults do not set a GTK name. Document choosing VGUI2Classic in
GTK settings; do not infer a profile from a stale Plasma/global/Union choice or
force those settings during package installation.

## VGUI-A4 — P1: existing tests contain Vapor-only assumptions

`--theme` is not sufficient for a new family. The GTK checkers stage it under
the name Vapor, read `Vapor.colors`, and expect Vapor selection/foreground/art
values. Widget Factory, behavior checks and mutation fixtures also contain the
Vapor name or fixed RGB values. The Adw checker has a fixed 27-role palette and
additional literal fill/foreground assertions.

Introduce named family expectations for discovery, KDE-derived roles, approved
contrast overrides, theme roots and optional libadwaita profiles. Keep all
existing Vapor gates. Add VGUI controls that reject wrong blue, white-on-gold,
dimmed dark selected text, wrong actual surfaces and the measured weak focus.
Require real pixels and adjacent backgrounds, not only variable-query labels.
The existing Adw focus comparison rounds before its gate; use an unrounded
comparison when extending the harness. Vapor's current 3.50:1 result is not a
demonstrated failure from that rounding issue.

## VGUI-A5 — P2: widget structure and artwork need separate GTK 3/4 work

Start from the maintained GTK 3.24 and GTK 4 branches independently. Audit
entries, selected text/rows, toggles, checks/radios/mixed states, switches,
scales, both spin orientations, notebooks, menus/popovers, sidebars, toolbars,
headers, tooltips, scrollbars, progress and semantic states. Preserve the known
inactive-label and spin-gradient fixes while replacing Vapor-specific styling.

GTK's [migration guide](https://docs.gtk.org/gtk4/migrating-3to4.html) and
[CSS-node reference](https://docs.gtk.org/gtk4/css-overview.html) explain why
selectors and widget assumptions cannot simply be shared unchanged. Prefer
CSS/SVG geometry for new classic controls where practical, and review retained
raster alpha, glyph contrast and 1x/2x treatment. Avoid runtime imports of the
entire Vapor theme followed by a few overrides: they leave unreviewed styling.
Do not add GTK 2 support.

## VGUI-A6 — P2: set an honest libadwaita matching boundary

The initial target is the tested dark/normal-contrast palette with native
Adwaita geometry. Preserve light/high-contrast fallback and upstream semantic
states. Do not load a full GTK theme over Adwaita or globally disable providers.
The existing project's approach and the probe provide the starting mechanism.

CSS recoloring does not change StyleManager's system-accent API. Custom graphs,
hardcoded colors and local application styling can remain different; Mission
Center's own chart colors are not proof of a failed theme-controlled selection.
See [libadwaita styles and appearance](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.10/styles-and-appearance.html)
and [paired CSS variables](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.10/css-variables.html).
Flatpak remains a separate validation target. No universal-app or full-classic
Adwaita appearance claim follows from the color-profile experiment.

## VGUI-A7 — P2: packaging and validation must cover both families

The stager copies `usr`, so a new GTK folder is naturally included, but its
libadwaita asset and packaged-document list are explicit. Extend those lists,
staging tests and profile resolution. Existing dependencies already cover the
proposed native targets; no additional runtime theme engine is established as
necessary. A future version/tag/checksum/AUR update should follow testing, not
be produced as part of this audit.

Record real GTK 3, plain GTK 4 and libadwaita apps separately, plus live focus,
menus/dialogs, RTL, scaling and large text. The prior Vapor screenshots and
manual scaling result do not validate VGUI2. Favor static bevels and avoid a
new watcher or heavy effects, but measure render/startup/idle behavior before
making performance claims. Two-second idle samples alone are insufficient.

## Evidence, limitations and recommendation

Portable measurements and probe summary are saved in
[vgui2-feasibility.json](docs/audits/vgui2-feasibility.json).

Evidence directory: `/tmp/vgui2-port-audit-cewuc_6t`. It contains baseline hashes,
`palette-contrast.json`, `stylesheet-inventory.json`, `probe-adaptations.json`,
private candidate profiles/checker, failing candidate logs/captures and the
passing `pale-focus/results.json` with all 22 cases. Scratch case names still
say Vapor because the original harness was adapted privately, not redesigned.

Only palette calculations, source review and a disposable native Adw profile
probe were performed. No GTK 3/4 VGUI implementation was created; no current
Vapor support, live setting, released package or AUR recipe was changed.

Proceed with [the staged plan](vgui2-plan.md): establish the independent family
and contrast policy, parameterize tests, implement GTK 3 then GTK 4, validate the
Adw profile and shared-manager migration, then test real apps and package it.
