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
