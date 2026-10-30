# Vapor libadwaita compatibility plan

Date: 2026-10-30 (America/Phoenix). Agent: Codex (GPT-6).
Status: initial native color profile implemented and tested; broader validation
and Flatpak remain open. This feature is not yet in a published package release.
Base: `5dcae96`. Evidence and detailed findings: [audit.md](audit.md).

## Implementation status — 2026-10-30

| Stage | Current result |
| --- | --- |
| 1: separate profile | Implemented in libadwaita/vapor.css; 27 role definitions, guarded dark/normal contrast |
| 2: standard tests | 22 native Adw cases, six negative controls, native GTK/Widget Factory coexistence; broader widget inventory/accessibility remains |
| 3: activation | Implemented helper; 15 preservation/recovery tests pass; actual user overlay remains disabled |
| 4: applications/displays/performance | Upstream Adwaita demo 1.10.0 and GNOME Font Viewer 49.0 startup comparisons pass; short idle observations recorded; live fractional/GPU and broader interaction remain |
| 5: Flatpak | Deferred: no local Flatpak executable/runtime; no support claim |
| 6: packaging | Working-tree staging tool includes profile/helper/docs; published 1.0.3 recipe/tag/checksum unchanged pending a new release |

[LIBADWAITA.md](LIBADWAITA.md) contains current usage/support instructions.
The stages below retain the full roadmap and acceptance criteria; the table
distinguishes the implemented native milestone from remaining validation.

## Recommended target

Build an **optional Vapor color profile for libadwaita**, initially targeting the
tested libadwaita 1.10.0 / GTK 4.24.1 combination. Preserve Adwaita's widget
structure, spacing, shapes, responsive layouts and behavior. Match Vapor's
selection/accent pair and dark neutral surfaces through CSS custom properties.

This is a compatibility overlay maintained by this project. Libadwaita documents
application CSS customization; applying user CSS across unrelated applications
does not create an upstream-supported universal theme interface. Applications
with custom drawing or local color definitions can remain different.

The first profile applies only to effective **dark appearance with normal
contrast**. Light appearance and high contrast retain upstream styling. A light
Vapor palette or high-contrast recoloring would need separate design/testing.
Changing an app's appearance preference is not the overlay's responsibility.

A full recreation of Vapor's buttons, borders and other widget geometry is a
possible later project, after the color profile works. It needs its own selector
inventory and larger regression matrix; the current GTK stylesheet cannot
serve as a drop-in replacement for libadwaita's stylesheet.

## Investigation already completed

- Read matching libadwaita 1.10.0 source, installed headers/GI data and embedded
  CSS, plus current GTK/libadwaita and Flatpak documentation.
- Ran seven isolated native-widget experiments with temporary HOME/XDG paths,
  staged theme copies, private Broadway/D-Bus and no desktop interaction.
- Both `:root` and `window` token declarations produced Vapor's #569fcc accent,
  #1f1f26 suggested-button text, #24272c window and #151c23 view definitions.
  The sample button and action-row allocations stayed identical to baseline.
- Dark-only/normal-contrast guards left light and high-contrast appearances
  outside the overlay. All seven processes exited normally with empty stderr.
- Confirmed legacy named colors and StyleManager's accent API can remain stock
  despite the CSS change. Plain GTK Widget Factory is not a libadwaita test.
- Existing user `gtk.css` imports KDE's `colors.css`; neither file was modified.
  No production overlay, activation helper or libadwaita test was installed.

Scratch evidence: `/tmp/vapor-libadwaita-audit-vlq92pyg/summary.json`, with probe
sources, per-case results/logs and content-only captures alongside it. Temporary
evidence may disappear on reboot; the audit preserves the measured findings.

## Stage 1 — Maintain a separate color profile

Implemented file: `libadwaita/vapor.css`, kept outside `usr/share/themes/Vapor/gtk-4.0`.
Start with `:root` custom properties inside the tested dark/normal-contrast media
guard. Keep the normal GTK 3/4 stylesheets independent.

| Role | Initial target | Treatment |
| --- | --- | --- |
| Accent fill | `--accent-bg-color: #569fcc` | Exact Vapor selection blue |
| Text on accent fill | `--accent-fg-color: #1f1f26` | Required pair, not white text |
| Standalone accent text | Derived `--accent-color` | Preserve libadwaita's contrast adjustment |
| Window, header, dialog, popover backgrounds | `#24272c` | Validate each surface separately |
| View and primary sidebar backgrounds | `#151c23` | Keep foreground light |
| Ordinary surface text | `#eff0f1` | Match the existing Vapor GTK palette |
| Cards and raised surfaces | Start with `#2d3136` | Proposed tone; review layered contrast |
| Secondary sidebar, backdrop, overview, active toggles | Explicit inventory required | Prevent leftover neutral panels or unreadable states |
| Errors, warnings, success and destructive actions | Upstream initially | Retain semantic distinctions and their foreground pairs |
| Border/dim/disabled opacity, radius, motion, fonts | Upstream | Preserve accessibility and geometry helpers |

Do not import the existing full Vapor stylesheet. Do not set a global
`GTK_THEME`, replace libadwaita, or add a patched runtime dependency. Avoid new
image assets, blanket foreground rules and animation overrides.

Acceptance: zero parser diagnostics; expected computed/token and rendered
colors in native Adw widgets; unchanged tested allocations; readable normal,
selected, suggested, disabled and inactive controls. Record any roles that
cannot be reached with documented variables instead of concealing gaps.

## Stage 2 — Add libadwaita coverage to the standard suite

Implemented core tool: `tools/check-libadwaita.py`, using real Adw widgets on private
displays and loading the profile through temporary **user CSS**, matching the
intended activation mechanism. Compile-only or parser-only checks are insufficient.

Fixtures must cover:

- Adw.Window/ApplicationWindow, ToolbarView/HeaderBar, PreferencesGroup,
  ActionRow, SwitchRow, EntryRow/PasswordEntryRow, ComboRow and ExpanderRow.
- Navigation/overlay split views and both sidebar surfaces; cards, banners,
  status pages, toast overlays and tab/overview/toggle controls where available.
- Actual open menus/popovers, Adw.Dialog/PreferencesDialog and any separate
  native popup surfaces. Assert coverage of the dialog/popover root variables.
- Text and row selections, suggested/destructive actions, checks/switches,
  disabled and synthetic inactive states, RTL and effective keyboard focus.

Assertions must use real descendant foregrounds and rendered backgrounds, not
only `@theme_selected_*` lookups. Assert the dark accent pair, at least 4.5:1
normal-text contrast, visible focus and non-text control contrast where applicable.
Keep disabled-text handling distinct. Libadwaita's translucent row selections
need their own measured foreground/background treatment; do not force dark text
onto every selected surface merely because the solid accent uses dark text.

Add light/high-contrast baselines, runtime appearance transitions, reduced-motion
checks, scale-1/2 captures and geometry comparisons. Correctly composite snapshots
over the window background; handle out-of-sRGB computed colors when measuring
contrast rather than treating raw channels above 1 as ordinary 8-bit values.

Add negative controls for missing activation/import, wrong accent foreground or
background, missing contrast guard and a deliberate CSS error. Separately record
what the accent API/named colors report: CSS overrides do not change that API.

Also run plain GTK fixtures and all ten Widget Factory cases with the overlay
present to detect unwanted effects on existing Vapor GTK support. The current
suite does not inject this additional user stylesheet, so extend its staging
deliberately rather than assuming the existing passing run covers coexistence.

Once implemented, invoke the new tool from standard `tools/check-gtk4.py` with
failure propagation and evidence under `libadwaita/`. Require the needed Adw GI
data for that standard run; do not silently skip the new stage.

Acceptance: the new normal/negative controls and existing GTK 3/4 suites pass;
reports distinguish tested widgets/states from untested surfaces and app behavior.

## Stage 3 — Implement reversible native activation

Staged installed asset:
`/usr/share/steamos-vapor/libadwaita/vapor.css`.
Implemented helper source: `tools/vapor-libadwaita` with enable/disable/status and
dry-run operations. Installation copies assets; activation is a user action.

- Honor `XDG_CONFIG_HOME`. Add one identifiable managed import in
  `gtk-4.0/gtk.css`, preserving the existing KDE `colors.css` import and unrelated
  contents, permissions and user edits. Keep the profile in a sibling file with
  a relative import so its references are self-contained.
- Back up before a first modification. Repeated enable/disable must be
  idempotent; disabling removes only this project's managed content. Restore
  byte-for-byte when appropriate without discarding edits made after activation.
- Handle regular files, absent files, read-only paths and symlinks explicitly.
  Inspect link ownership/targets and avoid replacing or modifying an unrelated
  target without a clear, reviewable operation. Dry-run must show exact effects.
- Detect KDE or another tool rewriting/removing the managed import. Status
  should explain how to reapply it. Do not add a background watcher or change
  the user's selected Plasma/GTK theme to repair it automatically.
- Explain that native user CSS is shared by GTK 4 applications; it is not an
  app-specific selector. Do not launch apps with a replacement XDG_CONFIG_HOME,
  which would redirect their normal configuration.

Acceptance: disposable configuration tests prove preservation of the current
KDE import, unrelated CSS, later user edits, missing/broken targets, repeated
operations, failure recovery and clean removal. Live activation remains a
separate user action after the concrete result can be reviewed.

## Stage 4 — Validate real libadwaita applications and displays

Run the matching upstream Adwaita demo and at least one independent libadwaita
application, such as GNOME Calculator, in an isolated test profile. Calculator's
upstream build explicitly depends on libadwaita. Widget Factory remains the plain
GTK regression application, not the evidence for this stage.

Review resizing/narrow layouts, sidebar collapse, header bars, preferences,
dialogs, tooltips/popovers near screen edges, text selection, focus, inactive
windows, app-specific styles and custom drawing. Repeat the user's physical
4K/175% test with an actual libadwaita application; previous Widget Factory
results establish plain GTK coverage only. Include scale 100%/200% and movement
between differently scaled displays where available.

Compare baseline and overlay idle CPU/redraw behavior and interaction latency
on the same app/backend/hardware. An overlay that adds only variables should be
small, but performance is unmeasured until this comparison is performed.

Acceptance: record app/version, GTK/libadwaita versions, session/backend,
renderer, scale, screenshots, actions tested and remaining exceptions. Start the
support claim with the measured 1.10.0/4.24.1 target. CSS variables appeared in
libadwaita 1.6, but the guard uses GTK media queries introduced in 4.20; older
runtime support needs a separate tested design. Do not infer compatibility for
all 1.6+ runtimes or promise future libadwaita versions.

## Stage 5 — Validate Flatpak separately

No Flatpak executable/runtime was available during this investigation. This
stage is a proposal; native success does not establish Flatpak support.

Prefer an explicitly selected app's own
`~/.var/app/<app-id>/config/gtk-4.0/` directory. Stage a self-contained profile copy
plus a managed relative import there, preserving any existing app-local CSS.
Verify the actual in-app XDG paths/runtime and behavior first; Flatpak normally
gives apps separate configuration directories and host `/usr/share` imports
cannot be assumed available inside them.

Avoid broad filesystem grants or all-app permission changes. No permission
expansion should be needed for an app to read its own configuration, but that
proposed activation path still needs real runtime verification. Document
per-app opt-in, restart/update/removal, copied-profile version/hash and how to
refresh copies after a host package update. Native and Flatpak runtime versions
need separate test records. A GTK theme extension alone does not prove that
libadwaita consumes this overlay.

Acceptance: one selected real Flatpak app can enable/update/disable the profile
without unrelated file/config/permission changes, and fallback appearance stays
correct. If this stage is deferred, label the first milestone native-only.

## Stage 6 — Package and document the supported milestone

- Install the separate profile/helper and its instructions without activating
  user CSS in package install/upgrade hooks. Keep existing themes intact.
- Add `libadwaita` as an optional runtime dependency for this optional feature,
  while making its test requirements explicit for development. Do not change
  the package into a replacement libadwaita or mandatory GNOME runtime bundle.
- Update README, CHANGES, audit and port log with exact tested scope, known
  accent-API/custom-drawing limitations, light/high-contrast policy and rollback.
  Include the plan/support docs in package documentation when shipping the feature.
- Run the standard suite, negative controls and a staged package build before
  proposing a release. Do not alter the checksum/tag of the existing release.

Completion means an opt-in color compatibility profile with tested activation,
rollback, native application coverage and documented limits. Flatpak is included
only after stage 5 passes. Full Vapor widget geometry and an upstream-supported
universal libadwaita theme remain separate claims.

## Primary references

- [Libadwaita 1.10 CSS variables](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.10/css-variables.html)
- [Libadwaita appearance and accent handling](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.10/styles-and-appearance.html)
- [Matching 1.10.0 style-manager implementation](https://github.com/GNOME/libadwaita/blob/1.10.0/src/adw-style-manager.c)
- [GTK user stylesheet loading](https://docs.gtk.org/gtk4/class.CssProvider.html)
- [GTK CSS properties and media-query version requirements](https://docs.gtk.org/gtk4/css-properties.html)
- [Flatpak configuration locations](https://docs.flatpak.org/en/latest/conventions.html)
- [Flatpak filesystem isolation](https://docs.flatpak.org/en/latest/sandbox-permissions.html)
- [GNOME Calculator build dependencies](https://github.com/GNOME/gnome-calculator/blob/main/meson.build)
