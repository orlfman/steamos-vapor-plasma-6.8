# Firefox theme plan: Vapor first, then VGUI2 Classic

Date: **2026-10-30**, America/Phoenix.
Initial target: Firefox **159** on KDE Plasma **6.8.2**.
Findings: [firefox-audit.md](firefox-audit.md).

## Current direction

The user requested Vapor first, including private windows, then required the
Breeze-style UI to be **the default**, rather than a separate option. The
original color-only/AMO-first proposal is superseded for the complete setup.

A normal Firefox color-theme add-on cannot change widget geometry. The default
Vapor setup therefore includes `userChrome.css`, narrowly scoped
`userContent.css`, and a setup/removal tool. It applies colors and Breeze-inspired
controls together. The private start page is included; private indicators and
browsing behavior remain intact. Arbitrary websites are outside the style scope.

The setup window guides users through selecting Firefox's settings folder while
Firefox is closed. It preserves existing files, adds owned imports and enables
Firefox's stylesheet loader. Removal uses the same window. There is no need to
edit source files, use a terminal, or log out of Plasma during ordinary setup.

The static color component remains available for development and future signing.
It is not the default complete-theme installation path. The main ZIP uses
Firefox's custom-style support and does not install an unsigned add-on or turn
off signature checks. Custom Firefox styling needs version-specific maintenance.

## Stage 1 — Palette, identity and control design

Vapor uses the existing project palette: `#24272c` window, `#151c23` view,
`#eff0f1` text, `#569fcc` selection and `#1f1f26` selected text. Breeze-inspired
controls have restrained 3-pixel rounding, readable hover/pressed states and
visible focus, while keeping native fonts, control sizes and browser features.

The color component has its own stable add-on ID. Normal/dark variants use the
same Vapor palette, including the variant Firefox may use for private windows.
The complete setup also overrides the built-in private theme's window surfaces.

**Vapor:** implemented. **VGUI2:** pending; reuse the audited olive/gold pairs
with dark text on solid gold, and make a deliberate control-style decision.

## Stage 2 — Default setup, preservation and distribution layout

Implemented source layout:

```text
firefox/
  INSTALL.md                  plain instructions shipped as bundle README
  README.md                   source/maintainer documentation
  Apply Vapor to Firefox      desktop launch script
  COPYING
  dev-requirements.txt
  vapor/
    manifest.json             static color component
    userChrome.css            default colors and Breeze-inspired controls
    userContent.css           Firefox-owned pages, including private start
tools/
  vapor-firefox               setup/removal CLI and KDE dialog workflow
  build-firefox-themes.py      reproducible complete ZIP and color-component XPI
  check-firefox.py            actual browser-interface checks
  test-firefox-setup.py        profile-file preservation/conflict/recovery checks
```

The setup tool requires an explicitly selected, closed Firefox settings folder.
It keeps unrelated CSS/preferences, recognizes ownership markers and copied-file
hashes, refuses links/read-only/ambiguous edited files and uses a reversible
transaction for ordinary write failures. Removal also accounts for Firefox
persisting the stylesheet-loader setting in `prefs.js`.

**Vapor:** implemented with a first complete ZIP. Before public promotion,
review the KDE dialog flow manually and validate installation from the actual
extracted ZIP. Include profile migration and upgrade cases when the format
changes. Keep the setup finite; no background watcher or browser scripting.

## Stage 3 — Browser-interface testing

The default suite checks both Firefox designs, light/dark system appearance and
scales 1/2 in disposable profiles. It covers normal and first/new private windows,
Vapor surfaces, selected-tab labels/close icons, field/button/tab shapes, address
selection/focus, synthetic toolbar hover/pressed states, matching start pages
and no theme leakage into an ordinary local webpage. The private search field
must lose its original purple fill. Private badges remain visible.

The suite validates the static component with Mozilla's linter and verifies
reproducible ZIP/XPI builds. Setup preservation tests and an actual open-profile
refusal are mandatory. The initial browser case exercises removal through a
real browser restart. Four wrong UI rules must be detected: wrong toolbar,
unreadable selected text, purple private strip and rounded private tab.

**Vapor:** core automation implemented; results belong in
[firefox-vapor-validation.json](docs/audits/firefox-vapor-validation.json).
**VGUI2:** extend the same harness when its assets exist. Missing tools must
fail clearly rather than count as a pass.

## Stage 4 — Broader audit and visual acceptance

Still required before claiming comprehensive coverage:

- Full popup/menu/address-suggestion, bookmarks/history sidebar and Settings/
  Add-ons component coverage, including unsupported Firefox internals.
- Actual forced-colors/high-contrast renders, keyboard navigation and focus
  order, RTL and larger fonts. Existing media guards are not a full validation.
- Live KDE Wayland and 4K/175% scaling, normal/maximized/fullscreen windows,
  pinned tabs/audio indicators and interactions with existing user CSS.
- End-user visual feedback comparing the result with KDE Breeze. This is
  Breeze-inspired CSS; Firefox does not run KDE's Qt widget engine.
- Any performance claim needs matched real measurements. The implementation
  adds static styles and a finite setup helper, not runtime browser scripts.

**Vapor:** pending broader audit/manual checks. **VGUI2:** pending implementation.

## Stage 5 — Plain installation and removal guidance

Use the complete bundle's [instructions](firefox/INSTALL.md): extract the ZIP,
open **Apply Vapor to Firefox**, choose the action, find the settings folder using
Firefox's Help page, close Firefox, select the folder, then reopen Firefox.

Explain that choosing another color theme inside Firefox alone does not remove
custom UI styles. Returning to the original appearance uses **Remove Vapor from
Firefox** in the same setup window. Keep developer loading, signing and test
commands in a separate maintainer section. Do not make Breeze styling an opt-in.

**Vapor:** written; manual walkthrough remains part of public-release review.

## Stage 6 — Release and package integration

- Finish the remaining audit and test the extracted default bundle from its
  own launcher. Verify upgrade/removal using real preexisting appearance files.
- Publish the complete versioned ZIP and screenshots through GitHub when ready.
  Its contents must match tested hashes and preserve executable launcher modes.
- A future AUR update may install the complete assets and setup launcher, with
  the dialog dependency declared. It must not alter profiles during a root
  package transaction or silently force a browser appearance for every user.
- Keep Firefox optional for the desktop theme package. Changing a selected
  profile remains a user action through the setup window.
- If publishing the static color component on Mozilla Add-ons, obtain signing
  and test signed restart/update behavior. Label its smaller scope clearly;
  it cannot by itself supply the default Breeze controls/private-page styling.
- Keep ESR, Firefox derivatives, Flatpak and future Firefox releases as separate
  compatibility targets until tested.

**Status:** source development and test artifacts only. Public Firefox releases,
Mozilla submission and AUR Firefox integration are pending.
