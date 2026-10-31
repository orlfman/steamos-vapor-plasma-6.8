# Vapor GTK 4 port — work log

Date: 2026-10-30 (America/Phoenix). Agent: Codex (GPT-6).
Starting commit: `4abe95d19366a437144bc2f469657563c2d86baa`.
Reference: [audit.md](audit.md). This log records implementation, tests and gaps.

## Scope and guardrails

- User requested starting the port and documenting all work here.
- Build a separate `gtk-4.0` theme for native GTK 4 applications, initially
  tested on installed GTK 4.24.1. Preserve GTK 3.24 files and shared artwork.
- Keep Vapor blue #569fcc, full-selection text #1f1f26, and readable inactive
  selection text; no return to inherited Breeze blue.
- Full libadwaita reskinning and Flatpak distribution are outside this initial
  implementation. No global GTK_THEME, user CSS injection or session changes.
- No installation, commits, release/tag or GitHub/AUR publication in this task.

## 1. Baseline inspection

- Working tree began clean except the requested, untracked `audit.md`.
- Read audit.md, released GTK3.md/CHANGES.txt, GTK 3 theme and current package.
- Confirmed the GTK 4 audit's scratch evidence is available; implementation
  will replace its lossy sanitizer with deliberate property/effect conversion.
- Recorded SHA-256 hashes of all 170 tracked files in a private /tmp baseline
  so unchanged GTK 3/artwork can be verified at the end.
- Existing code is released as v1.0.2; the package recipe remains pinned there.

## Current status

First implementation milestone complete: separate GTK 4 CSS and a passing
native content-rendering suite are present locally. The port is not complete
or release-ready. No agent work is left running; see results/gaps below.

## 2. Initial stylesheet implementation

Added `usr/share/themes/Vapor/gtk-4.0/gtk.css`, starting from released v1.0.2's
GTK 3.24 CSS. It is an independent maintained copy, not an import of GTK 3 or
Breeze. Added `gtk-dark.css` as an explicit import of the same dark Vapor theme.

Conversion performed (the one-time converter is in the scratch directory's
companion `/tmp/vapor-gtk4-convert.py`; CSS is edited directly after generation):

1. Removed the 27 GTK 3 widget style-property declarations listed by the audit.
2. Converted all four `-gtk-icon-effect` uses to icon filters: dim -> opacity,
   highlight -> brightness, none -> none.
3. Converted all **16 radial image functions in 11 declarations** to standard
   radial gradients instead of deleting them. A balanced-parenthesis scan kept
   nested rgba()/color functions intact. Legacy normalized radii were mapped
   to percentage ellipse radii at the same origin; full visual equivalence of
   attention and overscroll effects remains to be checked.
4. Mapped `radiobutton` selectors to grouped `checkbutton` roots and current
   `modelbutton.flat` menu selectors to `button.model`.
5. Mapped spin-control child `entry` selectors to GTK 4 `text` nodes.
6. Added explicit GTK 4 rules for text children/selections, modern list/grid
   selections and descendant labels, column headers, dropdown arrows/buttons,
   popover `contents`/arrows, menu buttons, and headerbar window controls.
7. Added keyboard-focus outlines without changing widget allocation. The
   inherited wildcard reset otherwise suppresses outlines. Restored entry/spin
   outlines through `:focus-within` and keyboard-visible outlines for controls.
8. Added a reduced-motion media rule disabling transitions/animations. The
   attention/spinner rules inherited from the baseline still require a focused
   animation/idle-work review before a release; no performance claim is made.

Palette: #569fcc selection, #1f1f26 active selection text, #eff0f1 ordinary and
dimmed selection text. Inactive text selections use half-alpha blue; modern
selected list/grid rows stay full strength with dark descendant-label text.
Disabled modern rows use the existing insensitive colors. No PNG was changed.

Both GTK 4 stylesheet entries parse with **zero errors** on GTK 4.24.1. The
first implementation still contains some inherited legacy/deprecated widget
selectors; unsupported declarations are removed, but a dead-selector cleanup
and full widget coverage are separate follow-up work.

## 3. Native test harness implementation and corrections

Added `tools/check-gtk4.py`, using GTK 4 real widgets, model/view factories,
`Gtk.WidgetPaintable`, Gtk.Snapshot and the GSK Cairo renderer. It creates a
private Broadway display with its HTTP endpoint on a Unix socket. HOME and all
XDG settings/cache/data/state/runtime locations are temporary. Theme discovery
uses a temporary gtk-4.0/settings.ini, with no GTK_THEME override, and a test-only
named class marker appended only to the staged stylesheet.

Planned/implemented fixture: buttons, toggles, entries and selected text, off/on/
mixed checks, grouped radio checks, switch, scale/progress, dropdown, spin,
notebook, selectable label, text view, ListView and ColumnView with real selected
model items, headerbar and a real GMenu/PopoverMenu. The original capture plan included normal, hover, synthetic backdrop, RTL,
keyboard-focus, open popover and disabled states for both variants. Initial
experiments attempted that set; the final acceptance suite includes only the
five states validated reliably, as recorded below.

Harness issues encountered and corrected during development:

- Python's native GSK render-node bindings work here; a small private-display
  probe confirmed snapshot -> render_texture before choosing this approach.
- GTK 4.24 warns for the old prefer-dark setting. The harness now uses
  `gtk-interface-color-scheme` / InterfaceColorScheme for its variant request.
- The first ColumnView check inspected the first recycled factory label rather
  than the selected row. It now obtains the child of the actual selected
  GtkListItem, so a recycled unselected cell cannot give a false failure.
- Subwidget snapshots can have a smaller painted bound than their allocation.
  The renderer now supplies an explicit viewport. Full native-window snapshots
  were unreliable under the private Broadway display (empty render nodes), so
  captures use widget content; full-window/compositor validation remains open.
- The discovery marker has its own normal-state color but legitimate backdrop
  label rules can override it. Discovery is asserted before changing state;
  real selected-label foregrounds are checked again in backdrop/RTL states.
- All GLib callbacks capture exceptions and end the test with a failure rather
  than silently timing out or reporting success. Worker processes have timeouts
  and the private server is always terminated.

Restricted `tools/check-gtk3.py`'s stylesheet/fixture globs to `gtk-3*` so it does
not incorrectly parse the new GTK 4 CSS with GTK 3. Its GTK 3 assertions and
palette/contrast checks are unchanged. Actual GTK 3 CSS/assets remain untouched.


## 4. Rendering-backend limits found during implementation

- Reusing a window renderer across screenshots caused duplicate frame-submission
  warnings in experiments; repeated snapshots also sometimes returned no node.
  A dedicated, independently realized Gsk.CairoRenderer is now used for exports.
- Increasing delays and forcing repaint did not make sequential mutable scenes
  reliable on this private display. The final harness starts a fresh worker for
  each state/variant, configures its state before first mapping, renders once,
  then destroys the window/renderer. All final workers emit no stderr.
- Opening a second native popover during sequential capture was not reliable
  either. Popover/menu CSS and a real GMenu model are implemented, but the final
  suite does not claim to have rendered the open menu or dropdown popups.
- An early six-state run produced twelve pictures, including a nominal focus
  state. A stricter FOCUS_VISIBLE assertion showed that the headless display
  clears that state when mapping; merely producing a picture is not a focus
  test. Tried setting window focus visibility as well; it still did not prove
  keyboard-visible focus. That case was removed from the passing suite rather
  than replacing it with a fake success. CSS focus rules remain to be validated.
- Screenshots capture the real content grid rather than the full native window.
  A test-only surface class supplies the theme's background in its transparent
  areas, and an explicit viewport preserves its allocation. This is not proof
  of compositor shadows/decorations or every window-control state.
- Made fixture columns homogeneous so model/table/text controls receive normal
  space rather than being artificially squeezed. This changes only the test
  layout, not theme metrics.

These corrections are test-infrastructure decisions, not installed theme changes.

## 5. Final verification results

Commands run from this repository root:

```sh
python3 -I tools/check-gtk4.py --output /tmp/vapor-gtk4-port-ahh08if7/final
python3 -I tools/check-gtk3.py
```

| Check | Result |
| --- | --- |
| GTK 4 version tested | 4.24.1 |
| Parse gtk.css and its explicit dark entry | Zero errors |
| Relative imports/images resolve | Pass |
| Named discovery through isolated settings.ini | Pass; test class marker on a real widget |
| Native child nodes | Entry/spin use text; grouped check uses radio |
| Actual selected ListView/ColumnView model items | Dark #1f1f26 foreground in normal/backdrop/RTL |
| Ordinary button foreground | #eff0f1 retained in those states |
| Exact selection background in the normal render | #569fcc found |
| Normal/hover/backdrop/RTL/disabled content rendering | **10 passes**, five states x two variants |
| Worker warning/error output | Empty in every final worker |
| Normal vs requested-dark pictures | Pixel-identical for all five pairs, intentional for a dark theme |
| GTK 3.24.52 existing suite | Pass, including its palette/contrast and eight scale-1/2 indicator cases |
| Existing GTK 3 stylesheet and 110 PNG hashes | Unchanged |
| Source/package recipe and published version | Unchanged v1.0.2 |

Native snapshots and node diagnostics can be inspected in the output directory
above. Those /tmp outputs are disposable; the durable harness reproduces them
with any --output directory. No test screenshots are installed with the theme.

The GTK 4 suite intentionally uses scale factor 1 and synthetic inactive states.
It does not claim real compositor focus/backdrop behavior, full-window HiDPI,
GTK 4 indicator @2 parity, high-contrast interaction, or GPU performance. The
GTK 3 scale-2 checks are not evidence for GTK 4 scale-2 behavior.

## 6. Files changed in this milestone

- New: `usr/share/themes/Vapor/gtk-4.0/gtk.css` and `gtk-dark.css`.
- New: `tools/check-gtk4.py` (native GTK 4 fixture/isolated runner).
- Small test change: GTK 3-only stylesheet globs in `tools/check-gtk3.py`.
- New: this requested `gtk4port.md` implementation/work log.
- Updated: README development scope/check commands; CHANGES.txt milestone entry.
- Existing untracked `audit.md`: retained as the pre-port assessment, unmodified.
- No modifications to existing files under usr/, shared PNGs, aur/PKGBUILD,
  aur/.SRCINFO, Alacritty/Konsole colors or published release artifacts.

## 7. Remaining work, in priority order

1. Validate real keyboard-visible focus and focus geometry. Extend a backend
   that can exercise focus reliably; keep the strict assertion when doing so.
2. Render open dropdown and popover menus, including checks/radios, selected
   actions, disabled actions, arrows and menu placement. The CSS exists but
   open-menu behavior is not yet accepted by the suite.
3. Add GridView and broader modern-widget/state cases. ListView/ColumnView
   are covered; normal/hover/backdrop/RTL selected text and all disabled
   foreground/background combinations need fuller contrast measurements.
4. Validate grouped checks/mixed states and menu indicators at actual scale 2
   and fractional scales. Current GTK 4 tests render normal scale only.
5. Compare header/window controls, notebook, scrolling/overscroll and attention
   gradients against the GTK 3 reference. Gradients are converted, not erased,
   but exact effect geometry is not yet proven. Prune dead legacy selectors
   only once modern and retained deprecated GTK 4 widgets are mapped.
6. Exercise reduced-motion/high-contrast preferences, text scaling, accessibility
   navigation, and idle/active animation work. The media rule alone is not a
   completed accessibility/performance test.
7. Test real native GTK 4 applications and Plasma selection on Wayland after
   an authorized install. Keep full libadwaita reskinning and Flatpak promises
   outside this initial support boundary. Current tested minimum is 4.24.1;
   establish a lower version floor only with corresponding tests.
8. Before publication, finish release checks/package inspection, bump version
   and archive checksum, update .SRCINFO, and publish only when requested.
   The AUR recipe still downloads v1.0.2; do not overwrite that tag or source.

## 7a. Review fix (Claude Code, 2026-10-30)

Claude Code's audit of this milestone found an inherited Valve bug visible in
the backdrop renders: a disabled spin button "-" gets the generic
`button:backdrop:disabled` gradient as a grey box. Fixed in both GTK 4 and
GTK 3.24 with `background-image: none` on the spin buttons' backdrop:disabled
rules (horizontal and vertical). Both suites pass afterwards.

## 8. Handoff and reproduction notes

The work is local, uncommitted and unpublished. Nothing is installed or applied.
The final checks pass for the scoped milestone; the remaining gaps above are
explicit, not hidden test failures. No agent process is left running.

Run the two toolkit checks independently. GTK 4 requires gtk4/gtk4-broadwayd,
python-gobject, python-pillow and fonts. It starts each test state in a fresh
process against temporary settings and always tears down the private server.
The helper currently deliberately targets the installed GTK 4.24 API rather
than claiming compatibility with every older GTK 4 minor release.

Do not rerun the one-time scratch converter as a build step: GTK 4 CSS is now
maintained independently and has hand-written node/interaction rules after the
converted baseline. Do not edit GTK 3 CSS or recolor shared images to solve a
GTK 4-only problem; add scoped GTK 4 selectors/tests instead.


## 9. Codex follow-up audit of Claude's spin fix — 2026-10-30

User requested an audit of Claude's latest GTK 4 work. Read section 7a and the
exact two-declaration GTK 3 diff; inspected the GTK 4 counterpart and tests.
The detailed review is now at the top of [audit.md](audit.md); its historical
pre-port assessment is retained below the new review.

- Existing GTK 3 suite and ten-case GTK 4 suite pass.
- Separate scratch matrix tested fixed versus only-the-reset-reverted variants
  on both toolkits, horizontal/vertical, min/middle/max/disabled, normal/backdrop.
  Normal pictures are identical; inactive differences are limited to affected
  controls (16,666 pixels per toolkit), and enabled middle controls are unchanged.
  Claude's fix is correct; no introduced regression found.
- Found R1: checked buttons keep dark foreground at the root but their child
  labels become light in backdrop. Actual render samples are only 2.65–2.67:1
  contrast. This inherited palette/label issue is present in both toolkits and
  both spin-fix variants, not introduced by Claude's change.
- Found R2: both existing suites also pass with the spin fix removed. They need
  a behavior assertion for the image-layer reset and a wider combined-state
  matrix. A screenshot being generated is not an assertion that the fix remains.
- Saved evidence/negative controls under /tmp/vapor-gtk4-review-5cr7yo0m and the
  scratch launcher /tmp/vapor-gtk4-review-probe.py. Scratch-only GTK 4 deprecated
  helper calls were replaced with native APIs before the final matrix rerun.
- Updated only audit.md and this log. Preserved all user/Claude changes,
  including the unrelated kitty work. No theme/test implementation changes,
  installation, commit, GitHub/AUR update or release.

R1/R2 from this review are resolved in section 10 below; the broader port
checklist still remains.


## 10. Fix R1/R2 and prove the regressions — 2026-10-30

User authorized fixing both review findings. Starting work preserved all existing
uncommitted GTK/kitty changes; tracked source hashes were saved under
/tmp/vapor-r1-r2-nb2vm7dv/before.json for a final scope check.

### Changes made

- Added the same narrow rule to the GTK 3.24 and GTK 4 stylesheets:

  ```css
  button:backdrop:checked:not(:disabled) label,
  button:backdrop:active:not(:disabled) label {
    color: inherit;
  }
  ```

  This lets the checked/pressed button's existing foreground reach its child
  label, overriding generic label:backdrop only in those enabled states.
  It does not replace global inactive-label colors or dimmed text selections.
  No blue value, gradient, geometry, image or unrelated semantic color changed.
- Added tools/check-gtk-regressions.py and invoked it from both existing toolkit
  checker entry points. The old GTK 3 --baseline comparison mode deliberately
  skips modern behavior requirements; normal checking always runs them.
- Native fixtures contain toggled, pressed, ordinary and disabled-checked
  buttons plus eight spins (horizontal/vertical x min/middle/max/fully-disabled),
  in normal and backdrop states. They run in fresh private display processes
  with disposable theme copies/config/cache/state and no live settings access.
- Label assertions inspect the real child, not just the root button color.
  Both checked and pressed labels must be dark; ordinary labels remain light,
  and disabled checked labels remain insensitive. Contrast is measured against
  a background pixel located using the toggle's actual widget geometry.
- GTK 3 spins expose arrow CSS gadgets rather than separate GtkWidgets. Their
  style paths encode orientation, up/down, range and insensitive/backdrop state;
  Gtk.render_background draws each matching background onto Cairo. GTK 4 uses
  real spin child buttons, asserts native sensitivity, obtains native bounds,
  and samples the rendered background away from border/glyphs. A returned
  inherited gradient fails the flat-background assertion. 64 background cases
  total (32 per toolkit) are checked across normal and inactive states.
- Added tools/test-gtk-regressions.py to create six independent negative-control
  themes, removing only R1, the horizontal reset, or the vertical reset from
  each toolkit. Tests require the specific R1/R2 AssertionError so an unrelated
  import, backend or startup failure cannot count as success.
- GTK 3's test requirements now include python-pillow for pixel/contrast checks.
  README/GTK3.md describe the new behavior gates and negative-control command.

### Test sequence and results

1. Ran the new GTK 3 behavior checker before changing CSS: normal passed,
   backdrop failed R1 because the child label was #eff0f1. This demonstrates
   the new test catches the original defect.
2. Applied the scoped inheritance rule in both toolkits. New behavior checks
   pass; measured contrast is 5.37:1 (GTK 3.24.52) and 5.43:1 (GTK 4.24.1), in
   normal and backdrop. The theme's gradient values are unchanged.
3. Added the enabled pressed-label assertion and ordinary/disabled guard checks;
   both toolkits pass. All 16 backgrounds per state are flat as expected.
4. Ran all six negative controls: reverting R1 fails R1; reverting either spin
   reset independently fails R2, on both toolkits.
5. Tightened the negative test to require the intended AssertionError rather
   than any failure. All six controls still pass that stronger proof.
6. Complete tools/check-gtk3.py passes, including existing selection contrast
   and scale-1/2 indicator checks plus the new behavior gate.
7. Complete tools/check-gtk4.py passes its ten normal/dark renders, parser,
   discovery/selection checks and the new behavior gate.
8. Both new Python files and existing modified helpers pass syntax checking;
   Markdown links/fences and git diff whitespace checks are verified separately.

### Status and remaining limits

R1 and R2 are fixed locally and marked resolved at the top of audit.md. No
installed theme, user config, release tag/asset, PKGBUILD/.SRCINFO, image asset,
kitty file, GitHub or AUR package was changed. Nothing committed or pushed.

The original port's keyboard focus, open menus, live Wayland/HiDPI, accessibility,
reduced-motion/effects and wider application coverage remain separate work.
These fixes do not upgrade that development milestone to full GTK 4 support.


## 11. Installed GTK Widget Factory automation — 2026-10-30

User installed gtk4-demos and requested using Widget Factory for automated
testing. Starting repository is clean at 1f0b925 (v1.0.3 recipe pin); earlier
milestones are now released by the user's intervening workflow.

### Implementation

- Confirmed gtk4-demos/GTK 4.24.1, cc/pkg-config and private Broadway support.
  Widget Factory's CLI provides help/version, not an automation/screenshot mode.
- Read the [matching upstream source](https://github.com/GNOME/gtk/blob/4.24.1/demos/widget-factory/widget-factory.c)
  and [command documentation](https://docs.gtk.org/gtk4/gtk4-widget-factory.html).
  Identified application ID org.gtk.WidgetFactory4, GtkBuildable main-stack ID
  toplevel_stack and page1/page2/page3. The installed binary's actual widgets
  are tested; the UI is not reconstructed or replaced with a fixture app.
- Added tools/widget-factory-probe.c. The runner compiles it into a temporary
  shared helper, with -Wall -Wextra -Werror. LD_PRELOAD is set only for the
  final application child. It wraps public gtk_window_present, verifies the
  expected app/stack, selects the requested page before mapping and schedules
  a capture after layout. It never loads into the display/D-Bus wrappers or
  existing user processes. A changed upstream layout fails explicitly.
- The helper disables animations/cursor blink for captures, sets the requested
  color scheme, applies synthetic backdrop or RTL and verifies effective state.
  Mapping can reset backdrop flags, so state is reapplied immediately before
  allocation/capture. No keyboard/pointer events or app actions are invoked.
- Uses public gtk_widget_snapshot_child after settling allocation. Renders the
  selected page over the actual window CSS background with GskCairoRenderer,
  saving content-only PNGs. These are not window-decoration/native-surface
  screenshots. Deprecated style-context color/background helpers are narrowly
  wrapped for compile warnings; there are no private GTK APIs.
- Added tools/check-widget-factory.py. It creates disposable HOME and every
  writable XDG path, copies Vapor and appends only an unused named-color marker.
  Settings select that staged theme; GTK_THEME is cleared. Selection named
  colors must still match #569fcc/#1f1f26. The app's own CSS remains active.
- Each case gets a fresh private Broadway display and D-Bus session with no
  service directories. GDK no-portals prevents portal discovery. GPU rendering
  and Vulkan driver enumeration are disabled only in test children; Cairo
  handles exports. A Unix HTTP socket and private XDG runtime separate displays
  from the user's desktop. Process groups/timeouts clean up test descendants.
- The runner checks metadata/state, mapped controls, PNG dimensions, opacity,
  nonblank content and distinct page images. Retains per-case stdout/stderr,
  PNGs and results.json with binary/CSS hashes and warning counts. A failed run
  removes an earlier success report in the same output folder.

### Failed experiments and corrections

1. Default private D-Bus configuration attempted to start its own desktop
   portals/backends; GTK_USE_PORTAL=0 alone was insufficient. Replaced it with
   a service-free private bus plus GDK_DEBUG=no-portals. No user bus or config
   was changed. Failed private sessions were stopped.
2. Guessed gl-disable/vulkan-disable debug options were unsupported. Inspected
   the installed help and [GTK runtime documentation](https://docs.gtk.org/gtk4/running.html),
   then used GDK_DISABLE=gl:vulkan:offload. Vulkan enumeration still loaded the
   system RADV driver and emitted its non-conformance warning. Setting the
   [loader's documented driver filter](https://github.com/KhronosGroup/Vulkan-Loader/blob/main/docs/LoaderInterfaceArchitecture.md)
   VK_LOADER_DRIVERS_DISABLE=* for the child prevents that unused driver load;
   the warning is not filtered from stderr. No system driver settings changed.
3. GtkWidgetPaintable snapshots of the active demo page stayed empty across
   retries. Public child snapshotting succeeded, initially warning about pending
   GtkBox allocation. Explicitly consuming the page allocation before snapshot
   resolved that warning. Rendering the window CSS background beneath the page
   fixed transparent areas in the first proof image. Removed the unused paintable.
4. Page 3 emits a GDK frame-timing warning before the capture callback:
   gdk_frame_timings_submitted() called on submitted frame. Fresh displays and
   the native Broadway renderer did not remove it. A scratch debugger run with
   fatal warnings stopped in GTK/GDK's main-loop dispatch before the helper's
   capture. A minimal control stylesheet containing only the two expected named
   selection colors, with no Vapor styling, reproduces the same warning.
5. Kept that exact backend diagnostic visible in logs/report and counted it;
   normal mode accepts only that precise warning, rejecting all other stderr.
   Added --strict to reject it too. This is an observed non-Vapor reproduction,
   not a diagnosis/fix of the backend's underlying cause. No broad warning filter
   or theme change was used to produce a green result.
6. gresource CLI is absent; runtime GtkBuildable IDs provided the needed lookup
   without installing another package. An initial combined file-replacement
   patch was rejected by the patch tool; rewrote the new runner successfully.

### Validation and results

- Full run: python3 -I tools/check-widget-factory.py --output
  /tmp/vapor-factory-d4yo6hy1/full — PASS, ten cases on GTK 4.24.1:
  three normal pages, three dark-request pages, three backdrop pages and page 1
  in RTL. All content images are 1215x705. Mapped-widget counts are 320, 227 and
  431 for the respective pages (including internal widgets, not distinct controls).
- Three known Broadway frame-timing warnings were retained, one for each page-3
  case. No other diagnostics, including CSS parser warnings, occurred.
- Visually inspected real page-1, page-3 and RTL captures. A rotating demo image
  has its own black surface; the surrounding page now has the actual dark window
  background rather than transparent black. These inspections do not establish
  pixel-perfect behavior or exhaustive widget coverage.
- Wrong-blue negative control: copied Vapor under /tmp and changed only the
  selection named color to old Breeze blue #3daee9. The runner rejects it for
  the specific FACTORY TEST FAILED: wrong selection blue reason.
- Invalid-CSS negative control: another disposable copy adds the unknown
  vapor-invalid-property declaration. The parser reports it; the runner fails
  even though the application produced a screenshot and otherwise exited cleanly.
- Strict-mode proof: the three-page quick run fails on page 3's known timing
  diagnostic as intended. All failed controls leave no success results.json.
- Scratch/control output is retained under /tmp/vapor-factory-d4yo6hy1.
- Completion checks pass: Python AST syntax, git diff --check, trailing
  whitespace and Markdown fences. Starting tracked-file hashes confirm only
  README.md, CHANGES.txt, audit.md and this log changed; the two test tools are
  new. All theme/assets, prior test tools, terminal files and AUR files match.
  Process inspection confirms no private factory/display/test processes remain;
  the user's existing desktop portal processes were left running.

### Status and limits

README documents requirements/commands; CHANGES.txt and audit.md record these
results. This adds an optional application test alongside the narrower native
widget assertions, rather than replacing them. Requires installed gtk4-demos,
GTK 4.24+ headers/pkg-config files, pkgconf, C compiler, dbus-run-session,
python-pillow and fonts. Runtime IDs were verified specifically on GTK 4.24.1;
future Widget Factory layout changes may require updating the helper.

No theme CSS/artwork, installed theme/user settings, kitty/terminal files, AUR
recipe/metadata, release tags/assets, GitHub or AUR content changed. Nothing
committed or pushed. Earlier toolkit suites were not repeated because neither
their code nor theme/fixtures changed since their previous passing verification.

Remaining: true keyboard focus, popup surfaces, pointer interaction, live
compositor/GPU/HiDPI, accessibility, animation/performance and libadwaita checks.
This is scale-1 content rendering with synthetic inactive/direction states,
not complete GTK 4 coverage or a warning-free strict-mode result.


## 12. Make Widget Factory part of the standard suite — 2026-10-30

User requested running Widget Factory with the standard tests, then explicitly
authorized committing and pushing when complete. Section 11's optional runner
was still uncommitted at the start; this commit includes that implementation,
its documentation and the integration described here.

### Changes

- tools/check-gtk4.py now runs tools/check-widget-factory.py unconditionally
  after its native widget/parser and R1/R2 behavior stages. The worker mode
  returns before orchestration, so rendering workers do not start nested suites.
- Passes the same resolved --theme to every stage. When --output is supplied,
  application screenshots/logs/report go under widget-factory/ alongside the
  existing top-level widget captures and behavior/ subdirectory.
- Uses subprocess.run(check=True): dependency/startup/assertion failures in
  the application stage fail the standard command. No automatic dependency skip
  or reduced application case list. The final suite PASS prints only after
  every stage succeeds.
- README and the GTK 4 checker's help list the now-required gtk4-demos, GTK 4.24+
  development/pkg-config files, pkgconf, C compiler and dbus-run-session alongside
  existing Python/font dependencies. Standalone factory --quick/--strict remain
  available for targeted runs; the standard suite runs all ten default cases.
- Updated CHANGES.txt and the current audit summary. The exact known page-3
  Broadway warning remains retained/counted; every other diagnostic still fails.

### Verification

- Ran python3 -I tools/check-gtk4.py --output /tmp/vapor-gtk4-standard-suite.
  PASS: ten native-widget renders, normal/dark requests over all five states,
  each with zero parser errors and the expected Vapor selection palette.
- R1/R2 behavior stage passes: checked-label contrast 5.43:1 in both normal and
  backdrop; 16 flat spin backgrounds per state (32 total).
- The same standard invocation then runs all ten installed application cases
  successfully. It retains the expected three known Broadway warnings and no
  other diagnostics. Application images/report are under widget-factory/;
  behavior evidence stays under behavior/.
- Earlier standalone wrong-blue, invalid-CSS and strict-mode negative controls
  remain the proof that application assertions/diagnostics can fail the runner.
  They were not repeated because that runner/helper did not change here.
- GTK 3, theme CSS/artwork, terminal themes and packaging are unchanged; the
  independent GTK 3 suite was not repeated. Final syntax/whitespace, artifact
  inventory, scope and process-cleanup checks accompany the commit review.

The user-authorized Git commit and push follow these passing checks. This is
test integration and documentation, with no installation, release or AUR update.


## 13. User validation on a 4K monitor at 175% — 2026-10-30

The user set a 4K monitor to 175% scaling and tested the installed GTK Widget
Factory with the Vapor theme. After guidance to check appearance, clipping,
menus, focus and inactive states, the user reported: "everything looked good".

Recorded as a user-reported manual visual pass for this display configuration.
The report supplies useful live application/scaling coverage beyond the
automated scale-1 Broadway/Cairo captures. No theme adjustment was indicated.
The user did not provide per-control results or renderer/session metadata, so
the evidence does not establish every individual interaction/backend case.

Updated README.md, audit.md and CHANGES.txt to reflect this result and avoid
describing all live HiDPI validation as absent. Broader focus/popup interaction,
other display/scaling configurations, accessibility, animation/performance and
wider application coverage remain open. No code, theme assets, installed
settings or packaging changed; the unchanged software suites were not rerun
for this documentation-only update. Checked whitespace and Markdown fences.


## 14. Investigate libadwaita compatibility — 2026-10-30

User requested investigating a libadwaita port, adding findings to audit.md and
creating a plan. This authorizes investigation/planning beyond the initial plain
GTK scope; production implementation and live activation have not started.

- Read libadwaita 1.10.0 headers/GI data, matching upstream style-manager,
  settings and stylesheet sources, embedded installed CSS and official GTK,
  libadwaita and Flatpak documentation. Confirmed installed versions 1.10.0 and
  GTK 4.24.1. A guessed _defaults.scss source path did not exist; inspected the
  upstream directory and actual _colors.scss instead. GI resource access first
  required calling an Adw function to load the library; corrected the scratch
  resource-read experiment accordingly.
- Saved starting tracked-file hashes and source/probe/results under
  /tmp/vapor-libadwaita-audit-vlq92pyg. Existing user gtk.css imports KDE's
  colors.css; inspected it read-only and did not alter either file.
- Wrote scratch-only native Adw fixtures and a private-display/session runner.
  Seven cases compare named-theme selection, forced GTK_THEME, full CSS user
  import, :root/window color-variable overlays, light and high-contrast guards.
  All exit normally with empty stderr. Explicit follow-up assertions pass.
- Both variable-overlay scopes produce #569fcc / #1f1f26 accent fill/text and
  the intended window/view colors, preserving the two measured allocations.
  Legacy named colors and the style-manager API remain stock in that test:
  recorded this as an application/custom-drawing limitation, not a solved case.
- Captured/inspected content images. Transparent areas omit the window itself;
  alpha pixel checks confirmed their appearance is not a full-window rendering
  result. Used inherited values, actual label colors and geometry as evidence.
  Raw derived colors can exceed the sRGB range; production contrast assertions
  will need rendered/gamut-aware colors.
- The guard works on the tested current runtime, but GTK media queries require
  4.20+. Libadwaita 1.6's variable support alone is not enough to claim older
  compatibility for this design. No Adwaita demo or Flatpak executable was
  available, so real demo/Flatpak application checks remain planned.
- Prepended findings, measurements and limits to audit.md. Created
  libadwaita-plan.md with six stages: separate dark color profile, native Adw
  tests/standard-suite integration, reversible activation preserving KDE CSS,
  real application/display/performance checks, separate Flatpak validation and
  packaging/documentation. Added README/CHANGES pointers with no support claim.

Recommended milestone is an opt-in color compatibility profile; full Vapor
widget geometry is a later decision with a larger maintenance/test scope.
No theme CSS/images, existing tools, installed settings, release or AUR metadata
changed. Existing software suites were not repeated for documentation-only edits.
The scratch feasibility assertions are the only new runtime checks this turn.


## 15. Implement the initial native libadwaita profile — 2026-10-30

User authorized engaging the port. Starting tree was clean at 4694f03. Saved
tracked-file hashes under /tmp/vapor-libadwaita-port-3fzbtni2/before.json.
Implemented the native color-profile milestone; Flatpak and broader live
validation remain explicit later work. The actual desktop overlay stays disabled.

### Profile and activation

- Added libadwaita/vapor.css with 27 documented color-role variables under
  dark/normal-contrast guards. Retained upstream derived foreground accents,
  semantic colors, geometry, opacity helpers, fonts and motion. No import of
  the complete old GTK theme and no shared PNG/CSS/palette changes.
- Added tools/vapor-libadwaita: enable/disable/status/dry-run/JSON; default
  XDG_CONFIG_HOME or explicit test configuration/profile; GTK/libadwaita
  version inspection through stdlib ctypes without initializing GTK/display.
- Managed relative import and sibling profile keep KDE colors.css and unrelated
  contents intact. Backup/state checksums, ownership/regular-file checks,
  symlink/read-only/collision refusal, directory locking and transactional
  rollback support safe ordinary operation. Original bytes/modes and later
  user edits are preserved. Status detects externally removed imports and
  modified owned copies rather than overwriting them silently.
- Added tools/test-libadwaita-activation.py. Initial 13 scenarios passed; review
  added deleted-config/reapply and read-only-directory cases. Fixed reapply
  bookkeeping to remove only a newly created empty gtk.css on disable, even
  after an older config had been deleted externally. All 15 pass, including
  one deliberately injected write failure with exact file/mode restoration.

### Native fixture and transport

- Added tools/check-libadwaita.py. Real Adw windows/toolbar, preference/action/
  entry/password/switch/combo/expander/spin/button rows, native buttons/checks,
  list/text selection, banner/status/toast container and NavigationSplitView.
  Actual dialogs, popovers and PopoverMenu custom content exercise popup trees.
- Loads the actual profile through the activation helper into private user
  CSS beside an existing KDE-style import. A separate parser observes errors;
  query-label CSS consumes real inherited variables without installing the
  profile provider through a different mechanism. Baseline comparisons use
  the same controls, system accent and software display environment.
- Checks computed and rendered accent/text, selected-row contrast, effective
  visible focus/ring contrast, disabled guards, mapped surfaces, allocations,
  upstream semantic colors and unchanged light/high-contrast image pixels.
  Captures render over the real window background, with explicit scaled export
  and recorded native widget scale. Runtime dark/light/dark transitions run
  within one process rather than being inferred from fresh launches.
- First baseline contrast gate failed because upstream white/#3584e4 is 3.77:1.
  Kept baseline unchanged; the >=4.5:1 suggested-text requirement applies to
  the recolored profile, measured at 5.64:1. Selected row measured 7.84:1 in
  the focus case; its visible ring measured 3.50:1. Disabled text is distinct.
- The first dialog capture at 650 ms found an actual mapped Dialog with its
  floating-sheet content still hidden. Public allocation/frame requests did
  not complete it. Matching GTK/Adw source explains no-client Broadway frame
  throttling and Adw's two-tick opening sequence; no theme change was needed.
- Added tools/broadway-test-client.py, an original small stdlib implementation
  of the GTK 4.24.1 Unix-socket/WebSocket transport replies. Handles surface
  configuration and roundtrip acknowledgments, discards renderer payloads and
  fails on unknown operations; no keyboard/mouse/application actions are sent.
  Transport-only timestamps follow the upstream client's zero last-input time.
- Cairo as the native display renderer plus acknowledgments initially produced
  backend timing errors/connection loss. Switched native display rendering to
  GSK Broadway while retaining a dedicated Cairo renderer for PNG exports.
  Actual dialog/menu content now maps normally. No browser dependency was added.
- Two exact frame-timing diagnostics occur with unmodified baselines. Retain
  and count them, reject every other stderr line; --strict rejects them too.
  Do not claim warning-free strict-mode passes. A full 22-case run retained
  26 such messages; counts are timing-dependent, not a theme acceptance target.
- Initially setting backdrop immediately before paint invalidated its cached
  content: computed colors were correct but the pixel check saw the bare window
  background. Set synthetic state early and allow native redraw before capture;
  pixel assertions then pass. Popup/dialog assertions are retained, not skipped.

### Integration and regression proof

- Standard tools/check-gtk4.py runs native fixtures/behavior/Widget Factory,
  repeats those plain GTK stages with the overlay activated in temporary user
  CSS, then runs all 22 Adw cases, activation tests and six profile mutations.
  New --user-css staging options in Widget Factory/behavior runners exercise
  that same path. The behavior worker explicitly requests dark appearance in
  overlay mode, so it tests the active guard rather than an inert light state.
- Added tools/test-libadwaita-regressions.py. Wrong blue/foreground, missing
  activation, either missing appearance guard and invalid CSS all fail their
  intended ADW assertions. Disposable copies only. Existing six R1/R2 controls
  still reject their intended GTK 3/4 regressions.
- Complete standard GTK 4 run passes, with all ten original native captures
  pixel-identical to their overlay-enabled equivalents. Twenty Widget Factory
  cases run in total (ten bare, ten overlay). Complete GTK 3 suite passes.
- Integer scale-2 cases report native widget scale 2 and doubled capture sizes.
  Focus case verifies actual FOCUS_VISIBLE; it remains a synthetic public-API
  focus test rather than desktop keyboard-input/Wayland certification.

### Independent applications and performance observations

- Downloaded official libadwaita 1.10.0 and GNOME Font Viewer 49.0 source archives
  to the scratch directory. Built the matching demo's public-API sources and
  resources against the installed library, avoiding a new runtime/Sass build.
  Built Font Viewer with Meson/Ninja; existing development dependencies suffice.
  The initially considered Calculator needs absent GtkSourceView development
  files, so used this independent libadwaita app instead of changing the system.
- Added tools/check-libadwaita-app.py and tools/libadwaita-app-probe.c for optional
  repeatable startup checks of a selected actual binary/app ID. The temporary
  helper loads only into that private child, queries inherited color roles via
  temporary public CSS, removes the query styling, captures content and quits.
  No font installation, app actions or system application installation occurs.
- Baseline/profile pairs pass for both apps, with 196 mapped widgets for the
  demo and 76 for Font Viewer. Startup evidence does not cover every demo page,
  application menu or custom drawing operation.
- Added optional bounded idle sampling after capture/settling using process
  CPU and monotonic wall clocks. Over ~2 seconds: demo baseline/profile
  0.548/0.558 ms CPU; Font Viewer 0.591/0.609 ms. These are small isolated
  observations, not GPU, whole-desktop or statistical performance guarantees.

### Packaging, documentation and remaining scope

- Added tools/stage-package.py to prepare an empty payload directory with all
  existing theme/terminal data, separate profile, executable helper and support
  docs. Tested staging without installing/activating anything. The existing
  AUR recipe still references v1.0.3; editing it to require files absent from
  that old source tarball would be incorrect. A new release must update the
  recipe/version/checksum and use the staged new payload in the normal way.
- Added LIBADWAITA.md with opt-in/rollback/test/staging commands, version limits
  and known API/custom-drawing behavior. Updated README, CHANGES, audit and
  the plan's status table to distinguish the implemented native milestone from
  remaining roadmap criteria. No Flatpak runtime is installed/validated here.
- Broader tabs/overview/toast/secondary-sidebar interaction, screen readers,
  reduced-motion interaction, live Wayland/GPU, physical 175%/mixed-monitor
  checks and wider runtime versions remain. The user's earlier 4K/175% pass
  is plain GTK coverage, not a newly claimed Adw application result.
- Actual user overlay status is disabled, with no managed changes. Existing
  GTK CSS/artwork, terminal schemes, published package recipe/assets and user
  settings are preserved. Final scope/whitespace/staging checks accompany the
  commit review; runtime evidence remains in the scratch directory above.

Completion verification: final standard run passes all 22 Adw cases, 20 Widget
Factory cases, native/behavior stages, 15 recovery tests and six profile
mutations. Final scale/backdrop assertions pass; all ten plain GTK comparison
images remain identical. GTK 3 and the older six mutation controls pass too.
The staged payload contains 175 files; its executable/profile hashes and an
isolated installed-helper enable/status/disable round trip pass. Python syntax,
whitespace, local Markdown links and baseline scope checks pass. Private test
processes are closed; a real-config dry-run leaves status disabled. Existing
GTK/artwork/terminal assets and published AUR files match their starting hashes.


## 16. Audit the libadwaita implementation — 2026-10-30

User requested auditing the work. Reviewed clean commit 83b5736, including the
profile, activation/state/transaction code, test coverage, app probe and package
stager. Saved source hashes and scratch reproductions in
/tmp/vapor-adw-review-9u20g82e. No production/test implementation was changed.

- ADW-R1: reproduced successful removal of an original empty gtk.css after
  changing only created_import_file from JSON false to the string "false".
  State loader accepts it; disable trusts its truthiness. Original nonempty
  CSS was not deleted in this reproduction. The fix is strict type validation
  plus no-write malformed-state regression coverage.
- ADW-R2: appended guarded wrong actual-window background selectors to temporary
  profile copies. Both the #29362f and #555555 copies pass the complete 22-case
  suite despite wrong rendered surfaces and unchanged declared variables.
  The green example has 307,916 opaque wrong-color pixels. A measurement-only
  scratch checker reports grey-background focus contrast 2.36:1 versus the
  existing assertion's 4.74:1, exposing a false positive in its 3:1 gate.
  No acceptance assertion was changed in that scratch checker. Recommend real
  surface/adjacent-background pixel assertions and an additional mutation.
- ADW-R3: exercised the actual staging function with an audit-only one-byte
  source and usr/stage destination. It recursively includes its own output;
  stopped after seven copytree calls with an explicit audit cap. No real
  repository/source-tree recursive copy was run. Resolve/reject containment
  before creating output and add a bounded negative control.
- Tested a BOM/import idea too; the original fixture already has a parser
  error, so did not report that as a new defect. Did not manufacture a theme
  stylesheet issue from a pre-existing invalid input.
- Re-ran the normal 22 native cases, all 15 existing activation tests, six
  existing profile mutations and ordinary package staging: pass. This confirms
  the current suite's success does not cover the reproduced cases. Did not
  repeat unrelated GTK suites because their implementation/assets are unchanged.
- Prepended findings with source lines, reproductions, impact and recommended
  fixes to audit.md, and linked the open findings from the plan. Three P2
  issues remain open; this review applies no fixes or live settings changes.

## 17. Fix libadwaita audit ADW-R1–R3 — 2026-10-30

User requested fixing the three findings from section 16. Started at clean
commit 8722b7a; saved tracked-file SHA-256 values and all retained test evidence
under /tmp/vapor-adw-fixes-9dw66ri8. The profile and existing theme/artwork are
unchanged. No real overlay activation or package release is part of this work.

### Changes and regression proof

- Added malformed created_import_file coverage before changing the loader.
  The string "false" reproduction fails the new test on old code (r1-before.log).
  Added strict optional-boolean validation, preserving the older-state fallback.
  Tests cover strings, numeric booleans, null, arrays and objects for all three
  helper operations and compare all managed contents/modes after every refusal.
  A separate legacy-state test verifies originally empty and originally absent
  gtk.css restoration. All 17 activation/recovery tests pass.
- Added bounded staging tests using tiny disposable source fixtures. The nested
  usr destination fails the new test on old code (r3-before.log); copytree is
  mocked to raise immediately if reached, so recursion cannot occur. Resolve
  source/destination and reject containment before mkdir. Eight tests cover
  nested/normalized paths, parent-symlink aliases, existing empty source
  destinations, final symlinks, relative paths and allowed repository/external
  destinations. Allowed fixtures check real payload bytes and helper mode 0755.
- Extended the native Adw fixture with a text view and test-only selector
  classes. Rasterize the real widget CSS backgrounds over their ancestors,
  using the existing private Broadway display and dedicated Cairo snapshot
  renderer. Text-view captures include its internal text-area node. Retain
  per-role PNGs and RGB samples in metadata. Assert window/header/card/view and
  relevant sidebar/dialog/popover pixels independently of the color queries.
  All 22 native cases pass (native-surfaces/ and native-surfaces.log).
- Focus contrast now uses the pixel next to the actual ring in the same image.
  Store this measured background separately from numeric contrast metadata.
  The unchanged Vapor profile measures 3.50:1 against RGB 36,39,44; suggested
  button text remains 5.64:1. The fixture preserves baseline/profile geometry,
  light/high-contrast identity, semantic colors, transitions and 2x checks.
- Expanded six profile mutations to 15: grey/green wrong window surfaces,
  wrong header/card/view/sidebar/dialog/popover surfaces, plus a wrong local
  button-bar background that leaves the neutral roles untouched. That last
  case fails specifically at actual-background focus contrast, proving the
  denominator fix independently of the surface gate. All mutations fail their
  expected assertions (mutations.log); production CSS is never edited.
- Integrated the eight staging tests into tools/check-gtk4.py. The standard
  run passes all native/behavior/Widget Factory stages both without and with
  the overlay, 22 Adw cases, 17 recovery tests, 15 profile mutations and eight
  staging tests (standard/ and standard.log). Exact known Broadway timing
  warnings remain recorded/allowed; no broader warning exemption was added.
- Updated README.md, LIBADWAITA.md, libadwaita-plan.md, CHANGES.txt and audit.md
  with resolved findings, test counts, commands and limits. Original audit
  reproductions remain as historical evidence, with a resolution pointer.
- Staged the complete real payload under package/ and compared source bytes,
  packaged docs, profile, terminal files and helper mode 0755. Ran the staged
  helper through status/enable/status/disable/status with an explicit private
  config/profile; it restores the original KDE import and mode 0640 exactly
  (staged-helper-results.json). All ten plain-GTK PNGs are byte-identical with
  and without the overlay. Syntax, Markdown link/fence and whitespace checks
  pass. Final tracked-file hashes confirm existing usr assets, the profile,
  terminal colors and AUR files are unchanged (final-integrity.json). A read-only
  status query confirms the actual user's overlay remains disabled.

Native libadwaita remains opt-in and unreleased. The established live-GPU,
fractional scaling, accessibility, broader application/performance and Flatpak
work remains open. Existing AUR version/tag/checksum are unchanged.

## 18. Enable the live overlay and record application feedback — 2026-10-30

The user explicitly requested activating the overlay to test it on their system.
Read the activation guidance and helper, confirmed the repository was clean,
then ran status and enable --dry-run. Status was disabled and the preview listed
only the four managed GTK 4 configuration files.

Enabled through tools/vapor-libadwaita. Compared the live gtk.css against the
managed import plus its original bytes, verified the backup and original mode,
checked that the copied profile matched libadwaita/vapor.css, and confirmed KDE
colors.css was unchanged. Status now reports enabled with no profile update
available. The helper's backup remains available for disable/recovery.

The user subsequently reported Mission Center was "looking great". Confirmed
the running executable is /usr/bin/missioncenter and its installed native
package is mission-center 1.2.0-1.1. Added this successful user-reported visual
check to audit.md and updated the plan's live activation/application status.
The report does not specify a display scale, individual pages or performance
measurements. Those broader checks and Flatpak remain separate work.

The user then reported FFmpeg Converter "looks good as well". Added this as a
second successful user-reported visual check with the live overlay enabled.
No version, toolkit or broader functional/benchmark claim is inferred from that
feedback. Updated audit.md and the plan to include both application reports.

This follow-up changes documentation only. The previous automated suite results
remain applicable; no theme code, package release or AUR update was needed.

## 19. Publish the live-testing screenshot — 2026-10-30

The user supplied Screenshot_20261030_160538.png and explicitly authorized
pushing it to GitHub as testing evidence/example. Copied the original
3394x1264 PNG unchanged to
[the documentation screenshots directory](docs/screenshots/vapor-libadwaita-mission-center-ffmpeg-converter-2026-10-30.png).
It shows FFmpeg Converter GTK on the left and Mission Center on the right
during the previously reported successful live-overlay tests.

Added an inline README preview with a dated caption and linked the same image
from audit.md. Verified the image decodes, matches the source SHA-256 exactly,
and all updated Markdown links resolve. This adds documentation/evidence only;
no theme code, automated-test expectations or package release files change.

## 20. Make native libadwaita support standard — 2026-10-30

The user approved the tested native profile for the default installation.
Started at clean commit 7b6ae22 and saved tracked-file hashes/evidence under
/tmp/vapor-default-install-x_d6ke6a. Existing color definitions and theme artwork
stay intact; the feature's packaging and activation policy change for 1.0.4.

- Added a packaged XDG autostart entry, limited to Plasma, invoking
  vapor-libadwaita auto once per login. It follows the selected Vapor/Vapor-dark
  GTK theme and exits. Switching to another GTK theme removes only the managed
  overlay at the next login/auto run. Package transactions do not edit homes.
- Added a validated .vapor-libadwaita-disabled preference beside the managed
  GTK files. Explicit disable writes it transactionally with CSS removal;
  enable clears it. Automatic checks respect the preference. Foreign content,
  symlinks, read-only targets, invalid metadata and edited profiles retain the
  existing refusal/rollback protections. Status exposes automatic_enabled.
- Read the selected theme from user GTK 4 settings, then GTK 3 as fallback,
  without starting GTK or contacting the desktop. Malformed settings refuse
  automatic changes. Existing command-line enable/disable still work independently
  of the selected theme, and dry runs never write the preference.
- Added eleven activation/recovery tests and updated removal expectations for
  the persistent preference: all 28 pass. Coverage includes no-op other/missing
  themes, Vapor/dark activation, idempotence, switching away/back, persistent
  disable/re-enable, external CSS regeneration/profile updates, dry runs,
  preference collisions/symlinks, settings precedence, malformed settings and
  rollback of the preference with CSS after an injected write failure.
- Extended standard staging to include the login entry and full-resolution
  testing screenshot. Existing eight bounded staging tests verify these bytes
  and helper permissions, alongside source-containment guards. Desktop-entry
  validation passes.
- Full standard tools/check-gtk4.py run passes: native widget/behavior and both
  ten-case Widget Factory runs, overlay coexistence, 22 Adw cases, 28 recovery
  tests, 15 deliberately broken profiles and eight staging tests (standard/ and
  standard.log). The precise existing Broadway warnings remain allowed/counted.
- Updated README, LIBADWAITA.md, the plan, audit and changelog for standard native
  support and persistent disable. Broader live scaling, accessibility,
  performance and Flatpak validation remain separate.
- Built a complete private 1.0.4-1 Arch package before publishing. Inspected
  required payload bytes/helper mode and exercised the packaged helper through
  auto/status/disable/auto/enable/auto plus a switch to Breeze in an isolated
  configuration. Original KDE imports and mode restore correctly; the actual
  user's GTK configuration is unchanged. Evidence: preflight-build.log,
  preflight-extract/ and packaged-helper-results.json. namcap reports no errors;
  its warnings concern existing transitive QML/icon dependencies and dependencies
  it cannot infer from theme files/ctypes library loading.
- A dry run against the live user reports selected_theme=Vapor, status=enabled,
  automatic_enabled=true and no changes. Release packaging will use a new
  v1.0.4 source archive/checksum, leaving existing release tags untouched.

Implementation references:
[XDG autostart specification](https://specifications.freedesktop.org/autostart/latest/),
[GTK settings](https://docs.gtk.org/gtk4/class.Settings.html), and
[Arch package guidelines](https://wiki.archlinux.org/title/Arch_package_guidelines).

### Release 1.0.4 / AUR 1.0.4-1

- Committed the default integration as cce2438 and published a new annotated
  v1.0.4 tag. Earlier tags remain unchanged. Created the public
  [GitHub release](https://github.com/orlfman/steamos-vapor-plasma-6.8/releases/tag/v1.0.4)
  with activation/disable instructions and the tested native scope.
- Downloaded the real GitHub tag archive and recorded SHA-256
  f918d4b9762d2bb580a63e6655cb84886b74ecf4386ba1c11eec0c50d1ca6b44.
  Updated the tracked and AUR recipes together to 1.0.4-1, required Python,
  GTK 4.24+ and libadwaita 1.10+, and used the shared staging tool in package().
  Regenerated matching .SRCINFO using makepkg.
- Built the final package from that archive with its checksum enforced. Exact
  payload comparison against the tested preflight build passes, including the
  helper/login entry; packaged documentation matches the tagged sources. No
  user's live GTK files change during builds. Lint has zero errors and the same
  seven dependency-inference warnings. Retained release-build.log,
  release-extract/, release-source.json and package-lint.log in the scratch tree.
- The fresh AUR checkout initially lacked a Git author identity. Configured only
  that checkout with the existing project's identity, then committed/pushed
  6e7eaf8 to the existing AUR package. No global Git settings were changed.

## 21. Audit and plan VGUI2 Classic for GTK 3/4/libadwaita — 2026-10-30

The user requested an audit followed by a plan for matching VGUI2 themes.
Started at clean e626869. Reviewed VGUI/VGUIUnion schemes, global defaults,
historical preview, existing GTK CSS/artwork, native Adw tests, the shared
activation helper and staging. Read matching GTK/libadwaita documentation.

- Saved baseline hashes, measured palette contrast and counted literal colors,
  gradients and asset references under /tmp/vgui2-port-audit-cewuc_6t. GTK 3/4
  branches each contain 33 literal hex colors, 58 gradients and 110 referenced
  PNG assets; 30 images contain exact Vapor-blue pixels. No VGUI GTK family or
  native color profile currently exists in the repository.
- Classic light text on gold is 3.503:1; Union's dark text is 4.965:1. Original
  links/focus are also too faint for the proposed gates on olive surfaces.
  Dimmed selections require separate light foreground treatment. Recorded the
  values and recommended keeping Qt definitions untouched during this port.
- Built an audit-only color profile and a private palette-adjusted copy of the
  native checker. Kept actual-surface/contrast/geometry/appearance assertions.
  Derived gold focus fails at 2.38:1; Union gold fails at 2.63:1; #fff2c2 still
  fails at 2.98:1. A separate #ffffe0 standalone accent passes all 22 cases,
  measuring focus 3.19:1, suggested text 4.97:1 and selected-row text 5.53:1.
  Original gold fills remain unchanged. All processes use private XDG/display
  state; no candidate is copied into the real user configuration.
- Wrote vgui2-audit.md with prioritized findings, source inventory, measurements,
  prototype limits and implementation constraints. Wrote vgui2-plan.md with
  family/palette decisions, harness work, GTK 3 then GTK 4 styling, Adw profile,
  safe shared-manager migration, real app/display/performance checks and future
  packaging. Libadwaita's first milestone retains native geometry; full classic
  reskinning and Flatpak remain separate.
- Saved portable measurements in docs/audits/vgui2-feasibility.json and linked
  the reports from README/audit.md. The current production test harness remains
  unchanged; only the disposable checker used VGUI palette substitutions. No
  new theme, package version, AUR update or live theme switch is part of this work.

## 22. Implement the VGUI2 Classic GTK 3 milestone — 2026-10-30

User requested starting the port with GTK 3. Started at clean 7e63667 and saved
tracked-file hashes/evidence in /tmp/vgui2-gtk3-port-heua7u9x. Scope is the new
GTK 3 family, its testing and source-package staging; GTK 4/Adw VGUI2 and live
selection remain later work. Existing Vapor CSS/artwork, Qt schemes and the
libadwaita manager are unchanged.

### Theme and reference

- Added VGUI2Classic chooser metadata, standard GTK 3.0 import, maintained
  GTK 3.24 stylesheet and explicit same-palette dark entries. Used Vapor's
  tested node/state patterns and label/spin fixes as a compatibility reference,
  while authoring independent classic CSS. This avoids carrying all Vapor
  gradients/bitmaps into the new family or relying on a runtime Vapor import.
- Matched VGUI olive windows/content and gold fills; used Union's dark text on
  opaque gold and light text on dimmed selections. Added raised/sunken edges,
  square controls, bright dotted focus, readable links and semantic states.
  Preserved fonts/hit targets; kept traditional round radio indicators.
- Replaced bitmap requirements with six new code-native SVG glyphs. CSS paints
  their field, border and state, including disabled variants. No old raster
  image is modified. GTK 2 and GTK 4 directories are not created.
- Built a temporary Qt Windows reference with KColorScheme reading the actual
  VGUI.colors. The first compile needed the installed KF6/KConfig include
  directory; adding it fixed the build. Rendered offscreen with private settings,
  preserving the Qt palette/style and recording the GTK readability differences.
- A final secondary-text review found the first muted role at 3.717:1 on olive.
  Brightened it to #cbd2c2 and added explicit ordinary/secondary/entry contrast
  gates: 7.317 / 4.839 / 9.545:1. Disabled glyphs retain their intentionally
  subdued treatment. Final review also matched tooltip surfaces to the source
  olive palette and ensured selected disabled rows keep dimmed text; both have
  explicit style/render checks.

### Family-aware tests and mapped applications

- Added independent expected family roles derived from KDE schemes; selected
  foreground uses VGUIUnion for VGUI2. Ordinary GTK control text follows the
  Button role. An early combined run mistakenly used Window foreground for
  legacy Vapor (241,241,242 versus 239,240,241); using the correct Button role
  restores all prior expectations without editing any Vapor stylesheet.
- Parameterized GTK 3 discovery/staging/palette/artwork and shared GTK 3/4
  behavior tests. Default GTK 3 now checks both families. Explicit --family or
  --theme targets one; mutation copies use --theme and cannot recurse into their
  own mutation runner. Archived Vapor --baseline remains separate.
- Added Cairo-painted classic contracts: square corners, opposite raised edges,
  ordinary/entry/secondary text, pressed/checked/suggested/destructive fills,
  links, seven focus contexts and progress/trough contrast. Preserve unrounded
  gate comparisons. All six normal/hover/backdrop/RTL/fine-tune/disabled widget
  states and eight scaled indicator contexts render correctly.
- First actual-background check sampled the transparent offscreen corner and
  timed out after a callback assertion. Sample inside the frame instead and
  propagate failures out of the loop, so a wrong surface fails promptly.
- Added mapped native windows, dialogs, popovers, menus and file choosers with
  private HOME/XDG, service-free D-Bus and no live desktop input. Setting only
  GTK_THEME did not set Gtk.Settings' reported preference; set the preference
  inside the test process too. Images are GTK/Cairo exports of mapped widgets.
- Implemented a GTK 3.24.52 Broadway viewport/configuration client sharing the
  existing WebSocket transport. Verified character operations against matching
  upstream broadway.js; it sends transport replies, not user input, and rejects
  unknown commands. An immediate menu popup still had a 1x1 unallocated anchor;
  the same failure occurs with unmodified Vapor. Open it after the first layout,
  matching when a real click can occur. All five mapped scenes then pass with
  both themes, without adding diagnostic allowances.
- Tested installed Meld 3.24.1's real startup page with isolated settings/bus,
  without loading comparison files or activating actions. Retained its screenshot.
  This is a separate explicit --meld check; it is not silently skipped or made
  a runtime dependency. Native popup/dialog fixtures are standard-suite stages.

### Results, artifacts and remaining scope

- Both GTK 3 families pass the standard command. VGUI2 gold text is 4.965:1,
  links 5.590:1, destructive text 6.728:1 and progress/trough 3.848:1. Focus
  checks cover buttons/rows/tabs/modelbuttons/entries/check buttons/switches;
  the lowest captured ratio is 5.040:1. See portable JSON for final text metrics.
- Added 13 independent disposable regressions for palette, light-on-gold,
  dimmed text, actual surface, focus, bevels, SVG blue leakage, inherited labels,
  both spin orientations, parser errors and missing asset/entry paths. The CSS
  parser raises GLib.GError directly for an invalid property; require that exact
  error/name for this control instead of incorrectly requiring AssertionError.
  All 13 fail their intended gate. Six old Vapor GTK 3/4 mutations still fail
  the original R1/R2 gates after the shared harness changes.
- Ran the previous GTK 3 checker from the starting commit against Vapor and
  compared all 14 PNGs with the current checker: byte-identical. Full existing
  GTK 4/Widget Factory/coexistence/Adw suite passes too, including 22 Adw cases,
  28 recovery tests and 15 broken-profile controls. Ten native GTK 4 images are
  identical with/without the existing Vapor overlay.
- Added VGUI2-GTK3.md, native/Meld/Qt-reference previews and portable measured
  results; updated README, audits, plan and changelog. Extended source-package
  staging to include the new guide, linked plans/evidence/images and the GTK 3
  family through usr. Published AUR/version/checksum files are not changed.

Evidence includes standard-gtk3/, standard-gtk4/, final-vgui2/, meld-final-current/,
the failed/corrected window runs, mutation logs, old Vapor checker/renderings and
temporary Qt reference source. This is initial GTK 3 support, not completion of
the GTK 4/libadwaita port or live HiDPI/accessibility/performance validation.

## 23. Audit and correct the VGUI2 GTK 3 port — 2026-10-30

User request: audit the GTK 3 port and fix confirmed issues. Started from clean
`4edece99be07a7a8dce67c4f1f56e39746407f05`. Private evidence root:
`/tmp/vgui2-gtk3-audit-etqg0cc2`. Captured SHA-256 hashes before changes and
froze the original checker/theme from Git for an independent reproduction.

### Reproduce before fixing

- The frozen original checker passes a copy with every check/radio glyph
  suppressed by CSS, because its nonblank check sees the painted field/frame.
  Assets remain present and referenced, so this is a demonstrated rendering-test
  blind spot rather than a missing-file test. See legacy-missing-glyph.log.
- Added a mapped state scene with actual InfoBars, selected ListBox/FlowBox
  children, nested ordinary buttons and disabled selections, in active/backdrop
  subtrees. Sample computed label colors against adjacent native painted pixels.
  Before fixes, inactive warning/error text is 1:1, selected-row nested buttons
  2.377:1 and inactive FlowBox text 3.503:1. states-before retains all samples.
- Expanded painted focus coverage to selected/checked/pressed/suggested states.
  Pale antialiased dots measure 2.717:1 on gold; icon views have no painted
  outline. Additional compatibility menu-button coverage also found no outline.
- Added eight mapped notebook layouts for four tab positions and both text
  directions. Confirmed actual overflow/header nodes, then rendered their style
  paths against independently chosen symbolic arrows. Vertical tab headers
  incorrectly render horizontal icons. GTK does not publicly expose internal
  arrow contexts, so this gate combines mapped node evidence, synthetic GTK
  rendering and native screenshot inspection rather than claiming direct access.

### Corrections

- Give each InfoBar type an explicit backdrop rule so generic semantic classes
  cannot turn the inherited text into the fill color. Preserve semantic labels
  elsewhere. Warning/error contrast is now 11.661/9.056:1 in both states.
- Let selected descendant labels inherit from their immediate parent: plain
  labels follow the selected container, nested button labels follow the button.
  Add selected FlowBox label coverage and consistent disabled selection dimming.
- Use dark dotted focus on opaque gold and pale dotted focus on dark surfaces.
  Preserve pale focus for destructive buttons, including pressed states. Add
  icon-view and compatibility menu-button focus paths. All 20 painted cases
  pass; gold focus is 3.506:1 and normal cases retain their previous results.
- Use up/down overflow icons for left/right notebook headers. Keep horizontal
  top/bottom icons; native LTR/RTL screenshots show the expected orientations.
- Compare each check/radio render with its field before glyph painting, test
  unchecked/checked/mixed/hover/disabled states at 1x/2x and require checked and
  mixed artwork to differ. There are 28 classic indicator cases, with Vapor's
  existing eight unchanged.

### Harness corrections and final verification

- A standalone row-label StyleContext path does not inherit from an implied
  parent. Set an explicit row context as parent in the old synthetic assertion;
  retain the new real-widget checks as the integration proof.
- StyleContext's public debug output here lists native nodes without image
  properties. An initial notebook probe expecting those properties failed even
  for correct horizontal layouts; use named-provider GTK rendering instead.
- An initial mixed-as-checked mutation removed the last mixed.svg reference,
  so it failed the unused-asset gate before reaching the intended glyph gate.
  Append an overriding rule instead. Both assets remain referenced and the
  rendering gate independently rejects the incorrect glyph. No gate is relaxed.
- Standard GTK 3 checks pass for both themes, including seven mapped VGUI scenes.
  All 23 VGUI mutations fail at their intended gates. Six existing Vapor GTK
  3/4 mutation controls, isolated Meld 3.24.1 startup and eight staging checks pass.
- All 14 original Vapor GTK 3 PNGs remain byte-identical. Hashes preserve 170
  existing production payload/helper/AUR files outside the VGUI2 family. GTK 4/
  Adw production code and shared checks are untouched; their full-suite pass in
  section 22 is historical, with the original mutation gates rerun here.
- Save native state/notebook screenshots and portable before/after evidence;
  update the guide, audit, plan, README and changelog. Stage the linked images
  with the documentation, verify package contents and documentation links.
  This exposed an older README link to aur/PKGBUILD that only worked in a
  checkout. Point it at the repository so installed documentation resolves too;
  the recipe itself remains unchanged.

No demonstrated performance defect emerged from the stylesheet review; effects
remain static except the native spinner and no services/timers were added.
No comparative benchmark is claimed. Live VGUI2 scaling, full keyboard/
accessibility, broader app workflows, GTK 4/Adw and shared activation remain
later work. The user's active theme, runtime helper, AUR metadata and published
release are unchanged. The changes are committed/pushed as source work only.

## 24. Start the VGUI2 Classic plain GTK 4 port — 2026-10-30

User request: start the GTK 4 port. Started from clean
`7ccdf926ac05feff6379917b534059cc5c5d84f1`. Scratch evidence:
`/tmp/vgui2-gtk4-port-2yli_fgl`. Saved SHA-256 hashes for every tracked file and
exported the baseline commit to a private directory. Ran the complete previous
Vapor GTK 4/Adw suite there to establish comparison images before editing.

### Implementation and family support

- Created independent gtk-4.0/gtk.css and explicit gtk-dark.css in VGUI2Classic.
  Transferred the audited olive/gold palette, bevels, semantic colors, inactive
  label fixes and six unchanged SVG glyphs. Updated the theme metadata comment
  to cover both toolkits. No runtime GTK 3/Vapor import or new bitmap assets.
- Adapted GTK 4 text children, icon filtering, grouped checks, list/column/grid
  views, dropdown/popover contents, observed menu-model nodes, calendar grid,
  title controls and focus-within. Removed GTK 3 widget-specific properties and
  unsupported widget assumptions. Added a reduced-motion animation guard.
- Parameterized check-gtk4.py, check-widget-factory.py and its C probe with the
  existing independent family specification. The C probe verifies actual theme
  name, fixture marker and expected palette from the runner. Both family names
  are tested by default; Vapor's complete Adw/coexistence stages remain intact.
  Explicit --family selects one, and --theme avoids recursive VGUI mutations.
- Added check-vgui2-gtk4.py for real labels, nested controls, semantic messages,
  disabled selection, glyphs, focus, notebook arrows and actual menu/dropdown/
  file-chooser captures. Five cases cover normal/dark, backdrop, RTL and actual
  scale-2 windows; PNG exports apply the matching scale with native GTK/GSK.
- Added 19 disposable GTK 4 mutations for wrong palette/surface, nested and
  inactive labels, warning/error messages, hidden/replaced glyphs, weak/missing
  focus, sideways arrows, menu text, invalid CSS, missing assets/dark entry and
  both spin gradients. Every mutation must fail its specific assertion.

### Findings fixed during the port

- GTK 4 rasterizes the one-pixel dotted focus differently: an ordinary button
  measured 2.73:1. Widened the dotted ring to two pixels without changing
  allocations, retained pale focus on dark/red and dark focus on gold. Real
  normal/checked/pressed/suggested/destructive/entry/switch/row/flow cases pass.
- Initially assumed the compatibility button.model selector from the maintained
  Vapor GTK 4 additions. Actual node inspection showed modelbutton.flat on this
  GTK 4.24.1 installation. Used that observed path and tested real menu labels.
- GTK 4 notebook overflow nodes are GtkButtons with GtkImage children. Copied
  GTK 3 icon-source rules on the outer arrow did not control the visible child.
  A same-widget CSS-reference test also falsely accepted a wrong arrow; its
  independent mutation exposed that weakness. Replaced it with independent
  GtkSymbolicPaintable reference rendering and comparison of actual visible
  glyphs. The stylesheet paints one symbolic background glyph on the native
  button and hides its image child, keeping geometry/navigation intact.
- CSS icon-theme backgrounds do not resolve logical start/end like the
  direction-aware reference API. An initial extra RTL swap pointed the wrong
  way. Removed that swap and verified horizontal/vertical layouts in RTL too.
  The wrong-direction mutation now fails the glyph gate.
- CSS color compositing and SVG rasterization alter edge intensities at 1x/2x.
  Compare normalized occupied glyph support in logical pixels, averaging each
  scale block, with a 0.2 interior threshold and at least 0.85 intersection over
  union. This avoids claiming byte identity across different rendering paths;
  a sideways glyph fails. Original text/focus contrast thresholds stay intact.

### Harness corrections and diagnostic controls

- The native state matrix needs acknowledged frames to update focus snapshots.
  Reused the existing private Broadway protocol client. Use Broadway for display
  transport and Cairo for exported snapshots, as the existing Adw matrix does.
  A Cairo live transport produced a native render-node cache assertion.
- Reusing a server across workers and changing a mapped complex window from LTR
  to RTL also exposed Broadway render-node reuse failures. Start a fresh private
  display for each case and construct the RTL fixture in RTL before mapping.
  No failure/timeout is retried or silently skipped.
- Explicitly set/verify synthetic active/backdrop flags, clear initial focus
  before applying them, and retain actual label node paths for diagnostics.
  The original virtual-row mutation lost to a more specific activatable-row
  rule; use an overriding selector so it tests the intended label failure.
- Sampling the top-left window pixel accidentally tested the automatic titlebar
  instead of the client background. The wrong-background mutation caught that
  false positive. Sample empty client-area padding at the bottom instead.
- Preserve the original worker error before requiring acknowledged frames:
  palette/parser failures can legitimately exit before mapping any surface.
- Reproduced both frame-timing warning strings using a separate stock GTK
  window/focus/popover probe, without any project theme, saved in
  timing-control.py/log. Retain/count only those exact two strings and support
  --strict. Unexpected diagnostics and all CSS parser errors still fail.

### Verification, documentation and remaining scope

- Both GTK 4 family suites pass. VGUI2 has ten native and ten actual Widget
  Factory cases; its five deeper cases total 100 labels, 45 focus checks,
  70 indicators, 40 arrows and 15 popup/chooser captures. All 19 negative
  controls fail at their intended gate. Enabled text passes 4.5:1 and focus 3:1;
  solid-gold text remains 4.965:1. Temporary HOME/XDG and a service-free bus
  prevent user-file or desktop-service interactions.
- Ran the full existing Vapor GTK 4/Adw suite after the harness changes. All
  172 baseline PNGs are byte-identical, including its original native, Widget
  Factory, behavior, coexistence and Adw captures. Existing recovery/mutation/
  staging stages pass. Both GTK 3 families and all 23 VGUI GTK 3 controls pass.
- Separately ran plain VGUI2 GTK 4 with the existing Vapor Adw overlay staged
  into the private user config. Native/behavior/Widget Factory captures remain
  identical. This proves coexistence only; it does not implement a VGUI Adw
  profile or change the current activation manager.
- Added VGUI2-GTK4.md, native/Widget Factory/state screenshots and portable
  validation JSON. Updated README, audit, roadmap, prior GTK 3 guide, changelog
  and package staging/fixture seeds. Verify staged files and linked docs/images.
  Record protected payload hashes and live helper status before committing.

GTK documentation for checks/grouping, spin text children, column/notebook nodes
and symbolic snapshots is linked in audit.md. No performance benchmark is
claimed. Live Wayland/X11 and fractional scaling, full keyboard/screen-reader
checks, broader app workflows, Flatpak, VGUI2 Adw and shared activation remain
later work. The current release/AUR metadata, runtime helper/profile and user's
active theme remain unchanged. This milestone is committed/pushed as source work.

## 25. Audit and correct the VGUI2 GTK 4 port — 2026-10-30

User request: audit the GTK 4 port and fix findings. Started from clean
`1767843808fac5d19ed9d108bcaca8358381ad0d`. Evidence root:
`/tmp/vgui2-gtk4-audit-95m6pc8u`. Recorded all tracked-file hashes and exported
the original commit before changes for independent reproductions.

### Confirmed stylesheet findings

- Real GtkFrame and has-frame scrolled-window fixtures had zero border widths
  and transparent edges. GTK 4 paints these on the main nodes rather than the
  GTK 3 frame/border gadget. Corrected selectors and checked both framed and
  intentionally unframed windows. Cairo's one-pixel outside edge is antialiased
  (alpha 250 here), so verify its actual color/coverage as well as border widths.
- Vertical spin text inherited the olive window surface while the horizontal
  field painted the darker content color. Added the vertical inset field, kept
  its foreground inherited and verified disabled alpha 0.4. An initial explicit
  enabled foreground in the fix prevented dimming; the new disabled fixture
  caught that, and inheritance was restored before committing.
- Column-view cell padding/separator rules targeted a column node that does not
  exist. Actual requested column borders stayed zero. Moved rules to listview /
  row / cell, used left borders in RTL, and verified requested row separators.
  Restoring cell padding exposed a minimum-width warning because generic row
  padding adds space outside the negotiated columns. Set column-view row
  padding to zero and retain spacing on cells; minimum-size fixtures then pass.
- Application preview inspection showed a blank expander indicator. GTK 4's
  root is expander-widget, followed by box/title/expander. Actual collapsed and
  expanded glyph widgets allocated 16px but rendered nothing under the old
  selector. Corrected both glyph paths, collapsed RTL direction, title focus
  and title spacing so the inset ring has room around text.

### Dark-entry false positive and corrected coverage

- The frozen original checker accepted a gtk-dark.css with a deliberately wrong
  theme background, even with --dark. gtk-interface-color-scheme communicates
  an interface preference; it had not selected this legacy variant file.
- Add a dark-only unused marker to disposable copies and explicitly request
  normal/dark named variants with GTK_THEME in each private test process. Native,
  state and C Widget Factory probes verify the actual entry. Normal discovery
  and palette markers remain. The same bad dark entry now fails the palette gate.
- Tried the deprecated application-prefer-dark property while diagnosing; it
  selected the file but emitted a GTK warning. Replaced it with the documented
  per-process debugging mechanism, without adding any warning allowance. One
  compatibility color lookup in the native checker suppresses only Python API
  deprecation notices locally; GTK parser/runtime diagnostics remain strict.
- Move renderer realization after marker/palette preflight checks so an early
  failed assertion cannot leave a realized renderer to abort during disposal.

### New real-widget checks and harness corrections

- Add gtk4-audit-checks.py with 12 checks per main case: three frame variants,
  three spin fields (including disabled), two table/separator configurations,
  two expander glyphs and two paired native title-focus captures. Across five
  states/scales that adds 60 controls, plus 15 sequential text-selection tests.
- Testing several selections simultaneously cleared another widget's primary
  selection. Give label, entry and text view separate settled capture phases.
  Verify actual painted selection fills and solid ink in multiple columns so
  a lone caret cannot satisfy the test. Correct opaque and dimmed selections
  pass; deliberately wrong foregrounds fail.
- A transparent expander focus snapshot was initially judged using only fully
  opaque changed pixels, omitting its real outline. Composite over the sampled
  parent fill for native focus comparisons. Contrast thresholds remain 3:1
  for focus and 4.5:1 for enabled text.
- Repeatedly forcing focus on the expander container exposed a Broadway native
  render-node failure. A saved StyleContext probe also did not reproduce the
  actual title state. Use real focused title widgets with matched unfocused
  references, setting their synthetic state once before capture. This checks
  native drawing without claiming full keyboard navigation coverage.
  Padding the title enlarges the indicator widget's allocation to 16x24; compare
  its centered 16px glyph against the reference rather than requiring the hit
  area's allocation to equal the glyph's size. Keep the same overlap threshold.
- Keep worker stdout/stderr before transport teardown, so native failures retain
  their original evidence. Pace this audit's frame acknowledgements at display
  cadence rather than spinning the frame clock. Shared production code and
  other transport clients are unchanged; no retry or automatic skip is added.
- Expand VGUI2 GTK 4 mutations from 19 to 32: frame/scroll borders, vertical
  background/dimming, column separators/RTL/padding, actual dark entry, opaque/
  dimmed text selections and missing/RTL/unfocused expander controls. Every
  mutation must fail its intended assertion; all 32 do.

### Verification and preserved scope

- Full VGUI2 GTK 4 native, shared behavior, ten actual Widget Factory cases and
  five deeper matrix cases pass. Recheck coexistence with the unchanged Vapor
  Adw overlay against the exact final CSS. Existing Vapor GTK 4/Adw suite passes
  with the corrected shared variant markers and C probe.
- Of the earlier session's 172 Vapor PNGs, 171 are identical. One factory RTL
  capture differs only inside its application-owned image region at
  (273,110)–(378,165). A fresh frozen original runner and the updated runner
  produce all ten factory PNGs identically, including that region. Record this
  rather than asserting universal byte identity against a historical capture.
- Hash-preserve all 182 existing production payload/helper/AUR files outside
  VGUI2's GTK 4 CSS. This includes GTK 3, all six SVGs, Vapor, the Adw profile
  and manager. Update portable measurements, screenshots, guide, README, audit,
  plan and changelog; stage the new details screenshot and verify doc links.
- The active Vapor helper remains enabled. No live theme activation, release,
  version/checksum change or AUR push is included. VGUI2 Adw/shared activation,
  full keyboard/accessibility, live fractional scaling, broader app workflows
  and comparative performance benchmarks remain open. No additional production
  performance defect was demonstrated in the stylesheet review.

The new audit entry links GTK's frame, spin, column, expander and theme-variant
documentation. Before/after control data, the dark false-positive reproduction,
frozen-runner comparison and current measurements are retained in the portable
validation JSON. Commit and push this completed source audit per the standing
instruction; no package publication is part of this milestone.

## 26. Start the VGUI2 native libadwaita color port — 2026-10-30

User requested the libadwaita port after the plain GTK 4 audit. Started from
clean `8935129da5e15fcd9d16d8fb64367498fcc86e1e`; saved all 232 tracked-file
hashes and a frozen checkout in `/tmp/vgui2-libadwaita-port-6cbw54nx`.
This implements stage 5. Shared automatic activation/migration remains stage 6;
the existing Vapor helper and live user configuration are unchanged.

### Color profile and independent expectations

- Add `libadwaita/vgui2.css`: 27 paired/surface roles plus the separate pale
  `--accent-color` under dark appearance and normal contrast. Main/header/
  dialog/popover are `#4d5845`, content/sidebar `#3f4638`, secondary `#282f21`,
  cards/thumbnails `#56604e`, ordinary text `#fcfcfc`, solid gold `#958831`,
  selected ink `#181810` and standalone accent/focus source `#ffffe0`.
- Retain Adwaita geometry, system fonts, motion, semantic colors and helper
  opacities. No full GTK stylesheet import or global provider suppression.
  The effective app appearance still controls the guarded profile. Light and
  high-contrast renderings remain exactly equal to baseline fixture images.
- Read upstream libadwaita 1.10 color-variable, appearance and style-class
  references; inspect matching installed native CSS resources in an isolated
  process. There is no documented focus-opacity variable for the needed fix.
  The guide links the upstream references beside the relevant claims.
- Add `tools/libadwaita-families.py`, independently anchored in the existing
  KDE family palette and explicitly approved secondary/card/focus roles.
  Parameterize native fixtures, negative controls and application probes with
  `--family`, retaining Vapor as the compatibility default. Existing `COLORS`
  and environment helper callers remain usable.

### Focus finding and fixture corrections

- The first variables-only VGUI2 profile passes the original 22-case matrix.
  Expanding focus to actual cards reproduces **2.95:1** against `#56604e`:
  the earlier 3.19:1 main-window trial was insufficient evidence.
- Raise only button outline-color coverage from upstream 50% to **65%** within
  the appearance guard. Keep outline width, offset, shape and spacing native.
  Exclude disabled and destructive/error/warning/success action classes so
  their semantic focus treatment remains upstream-controlled.
- Capture the actual adjacent pixels, compare unrounded ratios at the 3:1
  gate, and retain measurements for upstream baseline focus without applying
  the project's custom-profile gate to those baselines. Final profile results:

  | Focus surface | Ratio |
  | --- | --- |
  | Main window | 4.23:1 |
  | Raised card | 3.84:1 |
  | View | 5.15:1 |
  | Primary sidebar | 5.15:1 |
  | Dialog | 4.23:1 |
  | Popover | 4.23:1 |
  | Menu | 4.23:1 |

- Early new popup-focus captures reported 1:1 despite a visible ring. Capturing
  the inner box cropped the outline and allowed negative pixel indices;
  capturing its immediate content node still displaced pixels relative to
  computed bounds because of native margins. Snapshot the mapped popup root
  for these new cases, keeping bounds and native painting in one coordinate
  system. Require visible focus and valid sample coordinates. Both popup types
  then pass without lowering a gate, forcing CSS geometry or retrying a test.
- Add six baseline/profile focus pairs (card, view, sidebar, dialog, popover,
  menu), giving **34** VGUI2 cases. Require native allocations, semantic colors
  and the system-accent API to match paired baselines. Gold suggested text
  measures **4.97:1**; the selected-row text measures **5.53:1**.
- Preserve all 15 original bad-profile scenarios and add weak-card-focus and
  wrong-standalone-accent controls. All **17** VGUI2 controls fail the intended
  assertion. The card mutation restores 50% and reproduces the original defect.
  VGUI2's brighter ring needs a lighter deliberately bad local background;
  retain Vapor's old bad-background value for its original control.

### Standard suite and independent applications

- Extend the default `tools/check-gtk4.py` flow to run each family's matching
  profile coexistence, native Adw matrix and negative controls. Keep the
  existing Vapor activation/recovery tests; do not imply VGUI2 auto support.
  The deeper plain GTK VGUI checks and all 32 mutations remain mandatory.
- Rerun the original Vapor 22-case matrix through both frozen and updated
  runners. All **128** native Adw PNGs are byte-identical. Its 15 negative
  controls remain passing. All **184** protected production assets, GTK 3/4,
  SVGs, Vapor profile, helper/autostart and AUR files retain their baseline hashes.
- The real-app C probe now receives independent expected family colors from
  the Python driver. Build with warnings as errors. Test matching upstream
  Adwaita demo **1.10.0** and installed FFmpeg Converter GTK **2.0.1-1** with
  private HOME/XDG, service-free session bus and Broadway display. Both their
  baseline/profile startup pairs pass. A Vapor demo startup pair passes too.
  No media is opened, conversion started or live app/session settings changed.
- Both families' 22 plain-GTK native/behavior/Widget Factory captures are
  byte-identical with and without their matching Adw profile. Real apps retain
  native shapes; these app checks cover startup, not full user workflows.
- Known Broadway timing diagnostics remain narrowly matched and recorded;
  unrelated stderr remains fatal. This is deterministic Cairo evidence, not
  a live GPU or keyboard-navigation claim.

### Packaging, documentation and boundary

- Extend the explicit stager and its eight containment/payload tests with
  `vgui2.css`, `VGUI2-LIBADWAITA.md`, portable evidence and two unmodified native
  screenshots. Verify actual staged profile bytes, all copied `usr` assets and
  helper executable mode. Test the final packaged documentation links too.
- Add `docs/audits/vgui2-libadwaita-validation.json` with case/phase colors,
  rendered surfaces, focus, geometry, API and baseline evidence plus real-app
  results. Update README, both GTK family guides, the Vapor Adw cross-reference,
  audit, VGUI investigation/status plan, changelog and this log.
- The full standard-suite result and packaged-file checks are recorded in the
  portable evidence. Scratch logs, frozen runners, failed experiments, native
  and application captures remain in the named temporary evidence directory.
- Read-only live helper status remains enabled, automatic enabled, no pending
  profile update. Do not activate VGUI2, change automatic theme detection, alter
  backup metadata, bump/tag/release a version or update AUR in this milestone.
  Stage 6 will implement tested shared activation and migration. Live fractional
  scaling, GPU/keyboard/accessibility, broader app workflows, Flatpak and
  comparative performance remain open. No speed improvement is claimed.

Commit and push the completed source milestone per the standing instruction.

## 27. Audit and correct the VGUI2 libadwaita port — 2026-10-30

User requested auditing the port and fixing findings. Started from clean
`f508f4b4f37fae2e2ea1fea1ba98f60ff31dddbc`. Baseline hashes and a frozen
checkout, failed probes, logs and native captures are retained under
`/tmp/vgui2-adwaita-audit-vvfis832`. The newest audit entry and portable audit
JSON distinguish current measurements from the historical stage-5 record.

### Four confirmed findings and corrections

1. **Checked text:** real ordinary GtkToggleButton labels retain `#fcfcfc`
   over native gray fills. Normal window/card text measures 3.53/3.29:1;
   pressed card text falls to 2.64:1. Set only enabled ordinary toggle label
   ink to `#181810`, including nested labels. Keep the button's currentColor,
   background blends, hover/pressed fills, geometry and disabled treatment.
   A private inherited mix keeps semantic variants native. Normal/hover/
   pressed checked text now measures 4.93–6.58:1 on both surfaces.
2. **Focus beyond suggested buttons:** old cases miss weak checked/input
   outlines. Card normal checked focus is 2.32:1, card entry/spin 2.53:1 and
   card check/switch about 2.95/2.97:1. Use dark inset focus for ordinary
   checked toggles and 80% pale coverage for checks/switches/entries/spins.
   Keep ordinary button focus at 65%; preserve widths, offsets and shapes.
   The wider matrix checks hover/pressed checked controls too, since merely
   making their pale ring opaque still fails against brighter pressed fills.
3. **Compound semantic focus:** exclusions on a button's own class miss
   destructive classes on menu/split parents. Native child outlines change
   from 50% to 65%. Three private inherited coverage/ink controls retain
   native semantic coverage and ink across direct, menu, split-main,
   split-arrow and checked destructive controls. Compare actual transparent
   native outline layers and semantic foregrounds to stock baselines.
4. **Plain-GTK contamination:** broader coexistence reveals a pressed gold
   button focus at 2.28:1. The earlier normal/backdrop/RTL captures did not
   exercise real focus, so color-only global button declarations leaked.
   Add local `--vgui2-classic-focus-color` beside the plain theme's existing
   focus roles; use those local values as profile fallbacks. Native Adw has
   no bridge value and gets its intended profile colors. Standalone plain
   theme appearance/geometry remains unchanged. Five deeper state/scaling
   cases pass with the profile, and bridge removal must reproduce failure.

The profile still maps 28 color roles. Its private percentages do not change
Adwaita's global helper opacities. Semantic variables and the original native
shapes, appearance preference, light/high-contrast styling and system-accent
API remain intact. The plain-theme bridge covers the bundled VGUI2Classic
theme; no universal compatibility promise is made for arbitrary GTK themes.

### Test fixture and failed experiments

- Add `tools/check-vgui2-libadwaita.py`: 50 real controls across window/card
  surfaces, including ordinary/flat/suggested/checked buttons, nested labels,
  check/switch/entry/spin controls, Adw action/entry/spin rows and semantic
  compound controls. Run six baseline/profile pairs: dark, light, dark HC,
  light HC, RTL and scale 2. This gives 12 cases and 600 focused/unfocused
  checks, with geometry/semantic/fallback comparisons against stock.
- Compare actual edge pixels against the same unfocused pixels. Include
  inset and outside rings while excluding caret/text regions. Enabled
  ordinary text uses the real label foreground and painted button fill.
  Gates use unrounded ratios; rounding is only for reports. Clip out-of-gamut
  foreground components to sRGB for report calculations, preserving native
  rendering. Semantic controls are compared to upstream, not given a claim
  of universal 3:1/4.5:1 conformance.
- Assert effective requested appearance, contrast, direction, native scale
  and Adwaita providers. Require target focus to be absent from each baseline
  and visibly established in each focused capture. Exact light/HC focused
  image equality and paired allocations guard the color-only boundary.
- Combined widgets/early focus changes initially trigger native Broadway
  render-node reuse assertions even on the stock baseline. Forcing native
  Cairo did not resolve it; revert that experiment. Serial mapped control
  views, a separate focus-parking widget and the existing transport yield
  valid comparisons. An intermediate baseline still had automatic entry
  focus; parking focus elsewhere corrects it. No retry or lowered gate.
- GTK rejects complex ancestor exclusions inside `:not()` on this version;
  use inherited private values rather than unsupported selectors. Upstream
  GTK CSS-node/focus and Adw role/appearance references informed the changes.
- Add optional native display-log retention to the shared test helper and
  use it in app/control checks. Native Cairo snapshots and Broadway transport
  remain separate; known timing warnings are retained narrowly and unrelated
  diagnostics still fail. No change to the runtime activation helper.

### Standard integration and regression proof

- Keep the 34 surface/appearance cases and original Vapor checks. The default
  GTK 4 suite now adds all 12 control cases for VGUI2 and repeats the five
  deeper plain-GTK state/focus cases during matching-profile coexistence.
- Increase Adw regressions from 17 to 25: weak checked focus, unreadable
  checked text, weak input focus, missing semantic-parent handling, altered
  check geometry, unguarded focused light appearance and a missing plain
  focus bridge. Existing invalid CSS, palette, surface and appearance/import
  tests remain. Match real selector specificity so mutations actually apply.
- The original plain-theme/profile pair fails checked focus at 2.30:1 in
  dark mode; the intermediate fixes reveal pressed focus at 2.28:1. The
  light/normal original case correctly passes with the guard inactive. An
  initial bridge-removal negative control omitted `--dark` and therefore
  passed; correct its requested appearance and rerun the complete VGUI2 suite.
- The final state review reproduces the same low text contrast on ordinary
  mouse-pressed/keyboard-activating buttons, plus weak ordinary hover focus.
  Extend dark ink/focus to those activation states and 80% focus to hover,
  retaining native fills and semantic inheritance. Exclude native link/OSD
  treatments and test them explicitly. Coverage grows from 40 to 50 controls;
  add an ordinary-activation text mutation, giving 25 negative controls.
  The complete 40-control standard suite passed before this extension;
  rerun every affected native/control/coexistence/regression stage afterward.
- The frozen original profile fails the final checker for checked text and
  retains before-fix focus/semantic data. The intermediate fixes expose the
  separate plain-GTK failure rather than hiding it under the earlier suite.
  Final results are in the audit and validation JSON files.
- Matching Adwaita demo 1.10.0 and installed FFmpeg Converter GTK pass final
  baseline/profile startup checks. Earlier converter attempts hit an EOF on
  the unstyled baseline, reproduced by the frozen original runner too. A
  later diagnostic run passes; retain the failures as an intermittent
  private-display limitation, without adding automatic retries or filtering.
  No app media/action or live desktop input was used.
- After the activation-state follow-up, the exact final-profile demo pair
  passes. The converter's new retest again fails on its unstyled baseline,
  now retaining the Broadway append_node_ops render-node reuse assertion.
  Keep the earlier converter pair labeled with its tested profile digest;
  do not count it as a clean final-profile converter retest.

### Evidence, packaging and boundary

- Refresh native/converter previews from unmodified final captures and add
  a matching demo image. Update the validation report and add
  `docs/audits/vgui2-libadwaita-audit.json` with original/corrected controls,
  coexistence failure, regression proof and application limitations.
- Update the profile guide, plain-GTK guide, README, audit, plan and changelog.
  Extend stager assets and all fixture seeds/assertions for audit/demo files.
  Verify final staged profiles, `usr` assets, document/image links and helper
  executable mode; retain the eight path-containment/payload tests.
- The only existing production GTK change is the local focus-color bridge
  in VGUI2Classic GTK 4; GTK 3, SVGs, Vapor, terminals, runtime helper/login
  behavior and release/AUR metadata retain their baseline hashes. The live
  Vapor profile is not replaced. Shared activation remains stage 6.
- Live keyboard/GPU/fractional scaling, full accessibility/semantic contrast,
  Flatpak and comparative performance remain unvalidated. These fixes add
  static color rules, with no runtime watcher or performance claim.

Commit and push the completed audit per the standing instruction. Final
standard-suite, preservation and package verification results are retained in
the linked portable audit report.

Final verification: 34 surface cases, 12×50 focused/unfocused control checks,
25 deliberate Adw regressions, five deeper coexistence cases and eight staging
tests pass. All 22 plain-GTK native/behavior/Factory PNGs match with/without the
profile; all 128 original Vapor Adw PNGs remain byte-identical. Preserve 183
protected production files; only the local VGUI2 GTK 4 bridge changes in `usr`.
The final 213-file staged payload matches source bytes and linked documentation.
The lowest tested ordinary focus is 3.1763:1 and ordinary text 4.5511:1. Final
demo startup passes; the converter's final retest remains blocked by its stock
Broadway assertion. Live Vapor status remains enabled with no pending update.

## 28. Release GTK/VGUI2 libadwaita as standard components — 2026-10-30

User requested publishing the GTK/libadwaita work, activating support by default
and updating AUR. Prepare **1.1.0 / 1.1.0-1** from `f7a4310`; working evidence
is under `/tmp/vapor-release-1.1.0-pliu11f1`.

- Complete shared automatic selection for Vapor/Vapor-dark -> vapor and
  VGUI2Classic -> vgui2, using actual GTK 4 selection with GTK 3 fallback.
  Keep one import/copied CSS file, backup, helper and Plasma login entry.
  Explicit `enable/status --theme vapor|vgui2` is supported; auto always follows
  GTK selection. Legacy enable without a recognized theme still chooses Vapor.
- Retain schema 1 and recognize omitted profile_id as legacy Vapor; validate
  added IDs, preserve backups/later CSS edits, use transactional swaps and
  share persistent disable across both families. Status compares updates to
  the active family and reports pending family changes separately. Profile
  file overrides remain diagnostic. Runtime validation uses the actual
  enable decision, including auto. No watcher or appearance/GTK choice forcing.
- Resolve profiles relative to both checkout and installed helper locations,
  making staged/package tests use their own bundled assets. Keep old managed
  filenames and markers, with no destructive migration.
- Extend recovery tests from 28 to 38; run against source and the packaged
  helper. Real legacy-helper upgrades cover missing/empty/KDE import CSS,
  later edits, Vapor/VGUI2 swaps and persistent disable. One initial test setup
  created its settings directory before a helper expecting an absent directory;
  fix setup order and rerun. Existing 28 checks also pass independently.
- Include audited GTK 3/4 profiles, Adw profiles, guides, screenshots and all
  release evidence in normal staging. Update release-facing documentation and
  mark stage 6 complete; earlier audits remain historical. Package installation
  itself does not write user homes or change selected themes. Matching support
  is active at the next Plasma login or `vapor-libadwaita auto`.
- Run complete GTK 3/4 checks for both families; inspect the actual Arch
  package, run packaged activation checks and verify copied bytes and links.
  Native GPU/fractional/accessibility/performance and Flatpak limits remain.
  The known optional converter Broadway baseline issue does not change the
  mandatory suite or claim a new desktop/runtime failure.
- Publish a tested immutable source tag and GitHub release, then update the
  AUR recipe/checksum/.SRCINFO from that exact archive and publish it. As in
  previous releases, main's AUR metadata follows the payload tag so its archive
  checksum does not recursively include itself. Root package transactions do
  not automatically edit running users' homes; upgrade users can run auto or
  log in again, then restart GTK 4 applications.

Exact results: [release-1.1.0-validation.json](docs/audits/release-1.1.0-validation.json).

Release verification completed: both complete GTK 3/4 suites pass; source,
staged and actual Arch-package helpers each pass 38 tests. Three real legacy
upgrade scenarios preserve backup bytes and later CSS edits. The final Arch
payload matches the tested package after dependency metadata refinement.
Namcap reports no errors; its four unused-dependency warnings cover required
Plasma/Breeze integration and GTK/libadwaita libraries loaded dynamically.
QML and hicolor dependencies are now declared explicitly.

Payload tag v1.1.0 points to 55dbb46. The tagged archive SHA-256 is
`3af8dee4ac4f768fbd7045c407396a5874e562a1f17808c7ef40b72e42c98c22`. The package is 1.1.0-1;
AUR metadata and generated .SRCINFO follow the immutable tag on main. An initial
archive comparison used the aur subdirectory as its root and stopped before
metadata changes; rerun from the repository root verifies every tagged path.
The correct 1.1.0 package is rebuilt and verified independently afterward.

Publication completed: GitHub v1.1.0 is public, non-prerelease and Latest.
AUR master commit d4729f8 is accepted; the public package heading verifies
1.1.0-1 and public committed .SRCINFO has the matching version/checksum. The RPC
cache still returns the preceding version immediately after publication; record
that cache delay rather than treating an accepted push as unpublished. No live
package installation or GTK choice change was performed for this release.

## 29. Add an AUR GTK/libadwaita activation notice — 2026-10-30

User requested terminal guidance after installation, following a live Vapor to
VGUI2 switch that left the previous libadwaita profile active until auto ran.
Create packaging revision **1.1.0-2** using the existing verified v1.1.0 archive
and checksum; no upstream source tag is replaced.

- Add the standard PKGBUILD install script, tracked alongside the recipe.
  Both post_install and post_upgrade print the same non-interactive notice.
  Explain selecting Vapor/Vapor-dark or VGUI2Classic in KDE's GTK settings,
  applying, saving work and logging out/back in. Include the normal-user auto
  command and app restart alternative, plus explicit-disable behavior.
- Only print text. Do not change homes, invoke the helper as root, restart
  applications, terminate sessions or perform live package installation.
- Regenerate .SRCINFO; syntax-check PKGBUILD and the script; run both hooks
  from the actual package under sh/bash, without input. All checks pass.
- Build with makepkg --cleanbuild --force --noconfirm. The exact .INSTALL is
  embedded; generated metadata matches. Compare all 276 non-metadata payload
  entries against 1.1.0-1: paths, bytes, modes and link targets are identical.
  Namcap reports zero errors and the four existing integration/runtime
  dependency warnings. GTK rendering tests are unchanged and not repeated.
- Update README, changelog, audit and portable evidence. Publish matching
  GitHub main and AUR packaging; 1.1.0 remains the upstream theme release.

Results: [aur-1.1.0-2-validation.json](docs/audits/aur-1.1.0-2-validation.json).
