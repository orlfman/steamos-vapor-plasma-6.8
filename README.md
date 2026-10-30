# SteamOS Vapor - Plasma 6.8

The KDE Plasma themes from SteamOS desktop mode (Vapor, Vapor for Steam Deck and
VGUI2 Classic), fixed and checked against Plasma 6.8.2, plus matching Konsole and
Alacritty colors.

Based on Valve's `steamdeck-kde-presets` 3.9.4-2 from the SteamOS 3.9 repository,
theme files only. SteamOS system files (configs, scripts, systemd units, Steam
shortcuts) are left out.

## What's in it

| Part | Path |
| --- | --- |
| Global themes: Vapor, Vapor (Steam Deck), VGUI2 Classic | `usr/share/plasma/look-and-feel/com.valve.*` |
| Vapor Plasma style | `usr/share/plasma/desktoptheme/Vapor` |
| Vapor and VGUI color schemes, plus Union versions | `usr/share/color-schemes` |
| Vapor GTK 3.24 theme | `usr/share/themes/Vapor` |
| Vapor Konsole profile and colors | `usr/share/konsole` |
| Steam Deck wallpapers (`SteamDeckLogo` is the themes' default) | `usr/share/wallpapers` |
| Steam Deck start menu icon | `usr/share/icons/hicolor` |
| Vapor Alacritty colors | `alacritty/vapor.toml` |

## What was fixed

The short version (details in [CHANGES.txt](CHANGES.txt)):

- VGUI splash screen ported from Plasma 5 code that no longer works.
- Global themes no longer reset your Alt+Tab switcher to one that Plasma 6 removed.
- Dead Plasma 5 settings removed.
- Wallpaper set the Plasma 6 way, so it works from `~/.local/share` too.
- VGUI: readable error/warning/success colors, and toolbars no longer turn
  Breeze grey when a window loses focus.
- Plain Vapor gets the Steam Deck splash.
- GTK 3.24: maintained stylesheet and standard theme-chooser entry, fixed
  inactive text selections, unused images removed, no startup warnings or blank
  hovered partly-checked checkboxes. GTK 2 support dropped.
- Konsole and Alacritty: black is a visible dark grey instead of the background color.

## Install

Arch: AUR package `plasma6-themes-steamos-vapor-fixed`, or build it from
[aur/PKGBUILD](aur/PKGBUILD) with `makepkg -si`.

Manually, for your user only: copy the folders under `usr/share` into
`~/.local/share` (for example `usr/share/plasma/look-and-feel/*` into
`~/.local/share/plasma/look-and-feel/`). For the whole system, copy `usr/share`
into `/usr/share`.

Then pick a global theme in System Settings > Colors & Themes > Global Theme.

### Using Union

The global themes keep the classic Breeze app style, since Plasma's Union style
engine is still in development and meant to be picked by the user. If you switch
apps to Union (System Settings > Colors & Themes > Application Style), also pick
**Vapor Union** or **VGUI2 Classic Union** under Colors. They are the same schemes
tuned for how Union Breeze uses colors:

- Union draws the keyboard focus ring at 30% strength, which was barely visible
  with Vapor's and VGUI's focus colors. Brighter focus colors make it a bit more
  visible than Breeze Dark's.
- VGUI Union uses dark text on the gold selection (white was 3.5:1, now 5:1).
  Union also uses the selection gold for checkbox fills and button borders, so
  the gold stays and the text changes.

Re-applying a global theme sets the plain Vapor/VGUI scheme again.

VGUI also uses the Plastik window decoration (`aurorae` package) and the
KDE_Classic cursor (`oxygen-cursors` package).

Alacritty: add the theme under `[general]` in `~/.config/alacritty/alacritty.toml`:

```toml
import = ["/usr/share/alacritty/themes/steamos-vapor.toml"]
```

## GTK 3.24 compatibility

The working tree targets GTK **3.24** explicitly. Its maintained stylesheet lives
in `usr/share/themes/Vapor/gtk-3.24/gtk.css`; `gtk-3.0/gtk.css` imports it for
standard theme choosers and direct CSS consumers. The obsolete GTK 3.18/3.20
copies are removed. GTK 2 and GTK 4 are not supported.

Vapor keeps its own styling and artwork. Its GTK selection blue/text now match
Vapor.colors (#569fcc / #1f1f26), including related accents and check/radio
artwork. It does not import Breeze GTK.
The previous gtk-3.20 stylesheet already worked under GTK 3.24; this update
makes the supported target explicit and fixes selectors that missed their
intended nodes. See [GTK3.md](GTK3.md) for validation, limits and check commands.

These changes are in release **1.0.2** (AUR `plasma6-themes-steamos-vapor-fixed`
1.0.2-1). When replacing an existing manual installation, replace the entire `Vapor` theme
folder rather than merging it, so obsolete versioned styles do not remain.

## License

The theme files are Valve's, shipped by Valve under the GPL (GPL-2.0-or-later
per the package and global themes; the Vapor Plasma style's metadata says GPL
version 3). Steam, Steam Deck and their logos are trademarks of Valve
Corporation. This is an unofficial repackage, not affiliated with Valve.
