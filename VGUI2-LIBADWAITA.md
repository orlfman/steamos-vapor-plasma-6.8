# VGUI2 Classic colors for libadwaita

Status: **initial color profile implemented and tested, unreleased**, 2026-10-30.
Tested with libadwaita **1.10.0**, GTK **4.24.1** and Plasma **6.8.2**.
The published AUR 1.0.4 package does not include this profile.

`libadwaita/vgui2.css` matches the VGUI2 Classic olive/gold palette while
retaining Adwaita's widget shapes, spacing and responsive layouts. It applies
only to **dark appearance with normal contrast**. Light and high-contrast
appearances retain upstream styling; the profile does not force dark mode.

![Native VGUI2 libadwaita controls](docs/screenshots/vgui2-libadwaita-preview.png)

## Colors and focus

| Role | Color |
| --- | --- |
| Window, header, dialog, popover | `#4d5845` |
| View and primary sidebar | `#3f4638` |
| Secondary sidebar | `#282f21` |
| Raised card and thumbnail | `#56604e` |
| Ordinary foreground | `#fcfcfc` |
| Solid selected/suggested fill | `#958831` |
| Foreground on solid gold | `#181810` |
| Standalone accent and focus source | `#ffffe0` |

The profile sets 28 color variables. The separate pale accent keeps standalone
text and focus readable without brightening the original solid gold selection.
Native 50% focus coverage measured **2.95:1** on an olive card, below the
project's 3:1 gate. The guarded button rule raises color coverage to 65%,
preserving native outline width, offset and geometry. Semantic destructive,
error, warning and success action classes retain upstream focus styling.
Accessibility helper opacities, semantic colors, fonts and motion are unchanged.

This uses libadwaita's documented [color roles](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.10/css-variables.html)
and [appearance behavior](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.10/styles-and-appearance.html).
CSS changes do not replace the system-accent API. Apps that draw their own
graphs or use hardcoded colors can retain different accents.

## Preview and tests

From a source checkout, run isolated tests with temporary user configuration:

```sh
python3 -I tools/check-libadwaita.py --family vgui2 --output /tmp/vgui2-adwaita
python3 -I tools/test-libadwaita-regressions.py --family vgui2
python3 -I tools/check-gtk4.py --family vgui2 --output /tmp/vgui2-gtk4
```

The default `check-gtk4.py` runs both families, including matching-profile
coexistence, native Adw checks, deliberate regressions and package staging.
VGUI2 has 34 native cases and 17 broken-profile controls. Its additional focus
cases cover cards, views, sidebars, dialogs, popovers and menus. Tests sample
the actual adjacent surface, compare unrounded contrast and preserve baseline
geometry, semantic colors and system-accent API values. Light/high-contrast
profile images must exactly match their upstream baselines.

The optional application checker also accepts `--family vgui2`:

```sh
python3 -I tools/check-libadwaita-app.py --family vgui2 \
  --application /usr/bin/ffmpeg-converter-gtk \
  --app-id com.github.pieman.FFmpegConverterGTK --output /tmp/vgui2-converter
```

The libadwaita 1.10 demo and installed FFmpeg Converter GTK both pass isolated
baseline/profile startup checks. The checker opens no media and sends no app
actions. These startup checks are additional evidence, not default dependencies.

![FFmpeg Converter GTK startup with VGUI2 colors](docs/screenshots/vgui2-libadwaita-ffmpeg-converter.png)

## Packaging and activation boundary

The working stager includes the profile at
`/usr/share/steamos-vapor/libadwaita/vgui2.css`, together with this guide and
evidence. **Automatic VGUI2 activation is not implemented yet.** The existing
Vapor helper/login selection behavior remains as documented in
[LIBADWAITA.md](LIBADWAITA.md). Selecting VGUI2 alone does not activate this
profile. Do not use the Vapor-only automatic decision as a VGUI2 switcher.

Tests supply the new profile explicitly to the existing helper inside private
configuration directories. Shared profile selection, backup-preserving
migration and persistent disable tests are [stage 6](vgui2-plan.md) and must
precede a default-installation release. This milestone changes no live settings,
published version or AUR package.

## Evidence and remaining validation

[Portable results](docs/audits/vgui2-libadwaita-validation.json) record native
colors, rendered surfaces, focus measurements, fallback/geometry comparisons,
application checks and standard-suite results. [gtk4port.md](gtk4port.md),
section 26, records implementation experiments and corrections.

The private display uses Broadway and deterministic Cairo snapshots. Focus and
backdrop are synthetic. Live keyboard navigation, Wayland/X11 GPU rendering,
fractional scaling, accessibility tools, scrolling/resize performance and
Flatpak require separate validation. No speed improvement is claimed.
