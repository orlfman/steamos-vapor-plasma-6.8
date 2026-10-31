# Firefox theme investigation: Vapor and VGUI2 Classic

Date: **2026-10-30**, America/Phoenix. Repository baseline: `32937d6`.
Status: **investigation complete; Firefox themes have not been implemented**.
Next steps: [firefox-plan.md](firefox-plan.md).

## Recommended result

Create two normal, installable Firefox color themes: **Vapor** and **VGUI2
Classic**. Users choose the matching theme inside Firefox. This can match much
of the browser's colors while keeping Firefox's familiar controls and layout.
Publish signed themes on Mozilla's add-ons website so installation and updates
are straightforward.

A complete recreation of VGUI2's square buttons and beveled edges needs a
separate custom-styling project. Keep that optional and separate from the first
release. Explain to users that choosing a desktop theme and choosing a Firefox
theme are separate steps.

## Evidence and boundaries

The installed browser is **Firefox 159.0-1.1**, from `cachyos-extra-v3`, build
`20261027211755`, source stamp
`5add844c26613d7e4d84c799d6e23cf987b1240d`. Its package depends on GTK 3.
The existing GTK 4/libadwaita overlay is not Firefox's browser-theme mechanism.
Do not add Firefox handling to `vapor-libadwaita`.

Read the theme palettes and Firefox's installed application code, without
opening a browser or reading personal profiles. The application archives use
Mozilla's optimized ZIP layout: Python's ordinary ZIP reader rejected the
directory, while bsdtar returned an empty listing. Reading the archive index
directly and validating extracted entry sizes/CRCs recovered the actual schema
and mappings. This extraction was confined to a temporary directory.

Inspected files include:

- `chrome/toolkit/content/extensions/schemas/theme.json` and `manifest.json`;
- `modules/LightweightThemeManager.sys.mjs` and `LightweightThemeConsumer.sys.mjs`;
- `chrome/toolkit/content/extensions/parent/ext-theme.js`;
- `modules/ThemeVariableMap.sys.mjs`, browser colors/sidebar CSS and built-in
  theme manifests.

[Portable evidence](docs/audits/firefox-feasibility.json) records versions,
source hashes, supported fields and contrast calculations. No proposed theme
was loaded, signed or published. There are no Firefox rendering, accessibility,
performance or compatibility test results yet.

## Ways to build it

| Approach | What it provides | Assessment |
| --- | --- | --- |
| Static Firefox theme | Declared browser colors; optional bundled artwork | Recommended first release: two small themes without executable code |
| Dynamic browser extension | Code that changes browser colors in response to events | Useful only if automatic desktop-family switching becomes a separate requirement |
| `userChrome.css` | Deeper changes to browser layout and control styling | Possible later VGUI2 appearance option; higher maintenance and more involved installation |
| `theme_experiment` | Additional experimental styling hooks | Unsuitable for ordinary Firefox release users |

Mozilla separates static themes from extensions that run code. A dynamic
extension uses the [theme API](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/theme)
and requests theme access. Reading desktop-specific information would need
an additional bridge, such as [native messaging](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Native_messaging).
That extra machinery has no role in the proposed first release.

The [experimental theme key](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/theme_experiment)
is restricted to development channels with an additional preference enabled.
Mozilla [does not support custom userChrome/userContent styling](https://support.mozilla.org/en-US/kb/firefox-advanced-customization-and-configuration)
as a stable customization interface. Browser updates can break those rules.

## What the normal theme can cover

The following fields are present in the **installed Firefox 159 schema and
theme loader**. Presence in the schema does not prove every visible component
uses the field; rendered verification remains required.

| Browser area | Candidate fields |
| --- | --- |
| Window/tab-strip surfaces | `frame`, `frame_inactive`, `tab_background_text` |
| Selected tab | `tab_selected`, `tab_text`, `tab_line` |
| Toolbars and icons | `toolbar`, `toolbar_text`, `icons`, `icons_attention` |
| Toolbar button states | `button_background_hover`, `button_background_active` |
| Address/search fields | `toolbar_field`, `toolbar_field_text`, focused/background/border variants |
| Selected address-bar text | `toolbar_field_highlight`, `toolbar_field_highlight_text` |
| Popups and selected suggestions | `popup`, `popup_text`, `popup_border`, `popup_highlight`, `popup_highlight_text` |
| Sidebar | `sidebar`, `sidebar_text`, `sidebar_border`, highlight/background-text pair |
| Firefox Home/New Tab | `ntp_background`, `ntp_text`, `ntp_card_background` |

A browser theme does not provide arbitrary website recoloring, uniform styling
for every internal page or extension, new widget geometry, or control over KDE
window decorations and native file dialogs. Website light/dark preferences
also need checking: theme color-scheme properties can influence them. See the
[theme property reference](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/theme).

### Firefox 157+ / Nova needs its own verification

Mozilla's [current static-theme guide](https://extensionworkshop.com/documentation/themes/static-themes/)
identifies Nova as a change introduced in Firefox 157. Its ordinary themes use
the operating-system accent for some controls; a theme cannot independently
set that global accent. Selected tabs also need deliberate colors because the
older separating shadow is gone.

The MDN reference documents further Nova limits: the address suggestions can
retain default popup colors, redesigned sidebar selection colors may ignore
theme highlights, and the loading indicator may ignore `tab_loading`. These
are documented constraints, not failures reproduced in a running browser here.

There is a documentation discrepancy: the static-theme guide lists sidebar
highlight support, while MDN describes those colors as ineffective in Nova's
redesigned sidebar. The installed loader accepts them, but that cannot resolve
what is painted. Test the actual sidebar before promising matching selections.

The installed browser also contains the older non-Nova path, where
`browser-colors.css` deliberately supplies blue/cyan links and focus colors.
The first release cannot promise complete removal of every non-palette accent.
Record the active browser design in test results; no personal preference was
read to determine which design this user's running profile uses.

## Palette and readability findings

Use the maintained project palettes rather than a generic Steam-like blue or
an unreviewed copy of the original VGUI scheme.

| Role | Vapor | VGUI2 Classic |
| --- | --- | --- |
| Window/toolbars | `#24272c` | `#4d5845` |
| Inset content/sidebar | `#151c23` | `#3f4638` |
| Raised surface candidate | `#2d3136` | `#56604e` |
| Ordinary foreground | `#eff0f1` | `#fcfcfc` |
| Solid selection | `#569fcc` | `#958831` |
| Text on solid selection | `#1f1f26` | `#181810` |
| Focus candidate where supported | `#569fcc` | `#ffffe0` |

Sources are `Vapor.colors`, `VGUI.colors`, `VGUIUnion.colors`, the maintained
GTK styles and libadwaita profiles in this repository. Vapor's KDE window text
is slightly different (`#f1f1f2`); the proposed common foreground follows its
view/button/GTK palette. VGUI2's dark selection text is already used in the
maintained GTK/libadwaita and Union variants. These choices do not require Union
or alter the desktop's widget style.

Calculated opaque-color contrast, using WCAG sRGB relative luminance:

| Pair | Ratio | Finding |
| --- | ---: | --- |
| Vapor ordinary text/window | 13.1310:1 | Good starting pair |
| Vapor selected dark text/blue | 5.6361:1 | Suitable for normal selected text |
| Original Vapor focus/window | 2.6442:1 | Do not copy as an essential focus indicator |
| Proposed Vapor blue focus/window | 5.1562:1 | Stronger starting candidate |
| VGUI2 ordinary text/window | 7.3172:1 | Good starting pair |
| Original VGUI2 light text/gold | 3.5026:1 | Fails the 4.5:1 normal-text target |
| Maintained VGUI2 dark text/gold | 4.9652:1 | Use the readable pair |
| VGUI2 gold/window | 2.0891:1 | Weak as the sole essential focus/selection indicator |
| VGUI2 pale focus/window | 7.3756:1 | Stronger starting candidate |

These calculations are not a Firefox accessibility certification. Actual
opacity, focus outlines, selected-tab boundaries and disabled/hover states
must be measured after implementation. A gold selected tab needs a distinct
indicator or a documented brighter fill if Firefox cannot provide a sufficient
boundary. Explicitly test the selected-tab close icon and audio indicators.

Toolbar hover/pressed colors need separate care: the normal theme API provides
state backgrounds without matching per-state toolbar icon colors. Filling a
pressed button with gold while keeping ordinary light icons would repeat the
readability problem. Start with darker state backgrounds and readable icons;
reserve solid accent fills for areas with a controllable foreground pair.

## Installation, signing and updates

Ordinary Firefox releases require [Mozilla-signed themes](https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/).
An unsigned ZIP/XPI placed in an AUR package is not a finished user-installable
theme. Temporary developer loading is useful for tests but does not survive a
normal browser restart.

Prefer two public Mozilla Add-ons listings. Users can open a theme page and
click its install button; Firefox handles listed updates. Signed downloads
can also be offered on GitHub, with a documented update strategy. Mozilla
describes the distinction in its [self-distribution guide](https://extensionworkshop.com/documentation/publish/self-distribution/).

Future AUR integration should provide documentation/links and, if useful,
verified signed files in a shared data directory. Installing an AUR update
must not rewrite personal profiles, install enterprise policies, force a theme
or disable signature checks. Firefox remains an optional application.

Theme selection belongs in Firefox's own theme manager. It should not need a
Plasma logout; verify immediate application and persistence with signed files
before documenting that behavior. Explain switching/removal through Firefox's
menus using [Mozilla's user instructions](https://support.mozilla.org/en-US/kb/use-themes-change-look-of-firefox).

## Testing, maintenance and effort

Firefox is available locally. `web-ext`, Node/npm, geckodriver, Python browser
automation clients and Xvfb are not currently available on PATH/in the checked
Python environment. No tools were installed for this investigation.

Use Mozilla's [web-ext validation/development workflow](https://extensionworkshop.com/documentation/develop/getting-started-with-web-ext/)
and a separate disposable profile for every browser test. Browser-interface
tests must inspect the actual tabs/toolbars and popup documents, not just a
webpage screenshot. [Marionette can control the browser interface](https://firefox-source-docs.mozilla.org/remote/marionette/Intro.html);
current [geckodriver UI testing](https://firefox-source-docs.mozilla.org/testing/geckodriver/Flags.html)
requires an additional system-access flag. That flag belongs only in the
isolated test process, never the user's normal browser setup.

The initial static themes need no background scripts, network polling or
desktop watcher. Their small static payload is a sound performance-oriented
design choice, not a measured speed or memory claim. Avoid animated artwork
and expensive effects. Custom CSS and automatic desktop synchronization would
create additional maintenance work.

| Work | Relative effort / uncertainty |
| --- | --- |
| Two static palettes and unsigned developer builds | Small |
| Browser-interface harness, state/contrast checks and documentation | Moderate; largest initial engineering task |
| Signing, public listings and restart/update verification | Moderate; also depends on Mozilla account access and review |
| Full VGUI2 geometry through custom CSS | Larger ongoing maintenance task |
| Automatic Vapor/VGUI2 desktop synchronization | Separate extension/helper project |

The implementation plan includes actual rendered tests, signing and plain
installation instructions before calling this ready for end users. Older
Firefox/ESR versions, derivatives and Flatpak builds remain separate test
targets; current documentation and one installed schema do not establish
their compatibility.
