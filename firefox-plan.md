# Firefox theme plan: Vapor and VGUI2 Classic

Date: **2026-10-30**, America/Phoenix.
Status: **planned; implementation has not started**.
Investigation: [firefox-audit.md](firefox-audit.md).
Initial browser target: the installed Firefox **159.0** on KDE Plasma **6.8.2**.

## Intended user experience

Offer two Firefox themes: **Vapor** and **VGUI2 Classic**. A user opens the
matching theme's Mozilla Add-ons page in Firefox and clicks the install button.
They can switch later in Firefox's **Extensions and Themes > Themes** page.
Explain that Firefox has a separate theme choice from KDE.

Use ordinary color themes for the first release. Keep Firefox's layout, icons,
fonts, hit targets and accessibility behavior. Describe the supported result
as matching browser colors; full classic VGUI2 widget shapes are a later option.
Keep user-facing instructions understandable without developer knowledge.

## Stage 1 — Agree on roles, identity and supported scope

- Name the themes Vapor and VGUI2 Classic; reserve a separate stable Firefox
  add-on ID for each under this project's identity. Do not reuse Valve/Mozilla
  theme IDs or imply official Mozilla/Valve authorship.
- Add a family specification with the audited window/view/text/selection
  pairs. Use existing project colors and retain provenance/license notices.
- Map every intended browser region to a supported theme field. Separate
  supported schema fields from visually verified coverage and known Nova gaps.
- Set selected-tab foreground/background deliberately. Check whether an accent
  fill plus supported tab indicator can identify the selected tab sufficiently;
  document a brighter derived fill if necessary. Avoid white-on-gold text.
- Use dark toolbar-button hover/pressed surfaces where the icon foreground
  cannot change with the state. Preserve distinct ordinary/selected text.
- Start with dark browser appearance. Trial `color_scheme: dark` with
  `content_color_scheme: system`; verify that existing Firefox website
  appearance choices still work and built-in page controls remain readable.
  Decide the final properties from those tests and document any influence on
  website light/dark preference. Do not edit the user's preferences.
- Use Firefox's supported static-theme manifest format. Version 2 is used by
  current Mozilla static-theme examples and the installed built-in themes;
  validate it with current tooling rather than copying extension migration
  rules blindly. Choose a minimum Firefox version from the fields actually used
  and the oldest browser actually tested, not from schema acceptance alone.

**Done when:** both role specifications and the initial support boundary are
written down; calculated text/indicator pairs meet their targets or have a
clearly identified browser limitation requiring rendered investigation.

## Stage 2 — Build isolated browser testing

Proposed source layout (not created by this investigation):

```text
firefox/
  README.md
  palettes.json
  vapor/manifest.json
  vgui2/manifest.json
tools/
  check-firefox.py
  build-firefox-themes.py
docs/
  audits/firefox-validation.json
  screenshots/firefox-vapor-*.png
  screenshots/firefox-vgui2-*.png
```

- Add development-only tooling for Mozilla's `web-ext` validator and browser
  automation. Pin the chosen versions and document setup for maintainers.
  No Node, driver or browser-automation requirement belongs in the user's
  theme package dependencies.
- Create fresh temporary Firefox profiles and dedicated test processes. Never
  attach to the user's existing session or copy their cookies, extensions or
  browsing data. Track and terminate only test-owned processes.
- Temporarily load a theme through the documented developer mechanism. Use
  an automation client that can inspect the browser interface. If using
  geckodriver, explicitly enable its UI-testing access only for that process.
- Capture the browser's version/build, theme ID, active Nova/sidebar design,
  scale, color-scheme/forced-color state, computed styles and screenshots.
  Establish that the theme actually loaded before judging colors.
- Support local offline fixture pages and synthetic address suggestions.
  Make no signed-install or restart-persistence claim from temporary loading.

**Done when:** an isolated baseline and deliberately wrong test theme can be
distinguished in the actual browser interface, with no normal-profile writes.

## Stage 3 — Implement both static themes

- Add the two manifest-only color themes and a reproducible ZIP/XPI builder.
  Keep signing separate from building; identify unsigned artifacts as developer
  builds. Use a standard manifest at the archive root.
- Set supported colors for tabs, window states, toolbars, fields, text
  selections, popups, sidebars and Home/New Tab cards. Avoid unsupported aliases
  and avoid relying on fields documented as ineffective in the active design.
- Start without images, JavaScript, content scripts, permissions, remote
  resources or animations. Add only small original preview/icon artwork if it
  helps users tell the two themes apart.
- Retain Firefox's security indicators, private-window markers, built-in page
  behavior and third-party extension content. Do not add userContent CSS to
  recolor websites or replace the user's homepage/new-tab extension.

**Done when:** both manifests pass Mozilla validation, use distinct stable IDs,
build reproducibly and load correctly in disposable profiles.

## Stage 4 — Audit rendered colors and behavior

| Area | Required checks |
| --- | --- |
| Tabs | Selected/unselected, hover, keyboard focus, pinned tabs, close icon, audio indicators, multiple windows |
| Window/layout states | Active/inactive, normal/maximized, horizontal and vertical tabs, collapsed/expanded sidebar |
| Toolbars | Back/forward/reload, disabled controls, menu buttons, hover/pressed states, bookmarks/find bars |
| Address bar | Focus, selected text, suggestion popup and highlighted suggestions using synthetic local data |
| Panels/sidebar | Main menu, bookmark/download panels, bookmarks/history sidebars, selected rows and keyboard navigation |
| Built-in content | Home/New Tab surfaces and cards; sample Settings/Add-ons pages to establish coverage limits |
| Appearance/accessibility | Existing light/dark website choices, private windows, forced colors/high contrast, larger fonts, RTL |
| Display | 100% and 200% automated trials, then real 4K/175% KDE Wayland visual checks |
| Recovery | Vapor to VGUI2 to built-in theme, removal, clean restart and update with signed artifacts later |

- Measure actual painted/composited text and essential focus/selection
  indicators where the theme controls them. Use 4.5:1 for ordinary text and
  3:1 for essential non-text indicators; do not treat every decorative border
  as an accessibility requirement.
- Keep browser-controlled colors and unsupported surfaces visible in the
  report. A field accepted by the API but ignored on screen is not a passing
  recoloring test. Resolve the conflicting Nova sidebar documentation against
  what Firefox actually paints.
- Add meaningful bad-theme controls: wrong palette, white-on-gold text,
  missing selected-tab distinction, wrong selected-text color and an ineffective
  theme-field typo. Require the relevant check to catch each regression.
- Record repeatable native screenshots and logs for both families. Headless
  or integer-scale screenshots do not establish live fractional-scale/GPU
  behavior. An optional idle/startup observation must use matched profiles
  and must not become a general performance claim.
- Make the Firefox check cover both families by default once the harness is
  usable. Keep it a dedicated browser suite alongside the existing GTK suites.
  Missing browser-test dependencies must be reported clearly, not counted as
  successful validation. Run unchanged GTK checks only if shared code changes.

**Done when:** both themes pass the supported matrix, limitations are explicit,
regression controls fail as intended and user visual review is recorded.

## Stage 5 — Write plain installation and removal instructions

The main instructions should describe clicks and visible names:

1. Open the linked Vapor or VGUI2 Classic theme page in Firefox.
2. Click the theme's install button and accept Firefox's confirmation.
3. To switch later, open Firefox's menu, choose **Extensions and Themes**, then
   **Themes**, and select the theme you want.
4. To return to Firefox's original appearance, select its built-in system theme
   on the same page.

Verify the actual button/menu names in the release browser before publishing
screenshots. Explain that the browser choice is separate from KDE's theme.
After signed-install testing, state whether it applies immediately; do not
copy the GTK/libadwaita instruction to log out of Plasma.

Put temporary-addon loading, signing, custom CSS and automation instructions
in a separate maintainer section. Do not present developer loading as a
permanent installation method. Include one screenshot per theme and a short
explanation of the Firefox-controlled colors that may remain.

**Done when:** a new user can install, switch and remove a theme from the
documented steps without using a terminal or changing advanced preferences.

## Stage 6 — Sign, publish and integrate

- Use a Mozilla Add-ons developer account to submit each theme for signing.
  Confirm the current static-theme metadata, license, privacy declarations and
  listing requirements at submission. Never place account credentials in Git.
- Prefer public listings for simple installation and Firefox-managed updates.
  If signed files are also distributed on GitHub, preserve the signed bytes,
  record their hashes and explain which channel supplies updates. Do not
  rebuild a signed XPI or change its ID between channels.
- Test the actual signed files on ordinary Firefox: fresh installation, theme
  switching/removal, full browser restart and an update. Signing/review is a
  release prerequisite; a temporary-addon test alone is insufficient.
- Include source and guides in the next appropriate project release. Add
  signed files to package staging only if their provenance, checksums and
  ongoing update route are settled. A shared data location such as
  `/usr/share/steamos-vapor/firefox/` is suitable for optional install files.
  An AMO-link-only integration is also valid and simpler to maintain.
- Keep Firefox optional. AUR installation prints a brief explanation/link;
  it does not alter profiles, auto-enable browser themes, write enterprise
  policies or weaken signature checks. Update README/changelog/package
  validation when real Firefox files are added.

**Done when:** two signed end-user themes are installable, update/restart tests
pass, browser instructions match the release artifacts and distribution checks
pass. GitHub/AUR promotion belongs to this future stage, not this investigation.

## Later options

Only after the static themes are stable, consider a separate VGUI2
`userChrome.css` appearance layer for square controls/bevels. Give it an explicit
Firefox-version support boundary, backup/removal procedures and its own tests.
Do not silently install it with the normal color themes.

Automatic desktop-family switching, Firefox derivatives, ESR and Flatpak are
additional projects/test targets. Validate each before promising support.

## Current completion

- Completed: local/source investigation, official-documentation review,
  palette contrast calculations, architecture recommendation and this plan.
- Pending: stages 1–6 above, theme implementation, browser rendering tests,
  Mozilla signing and all Firefox release/distribution work.
- No browser profile, live theme, AUR metadata or release version was changed
  as part of this investigation.
