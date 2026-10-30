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
| Vapor and VGUI color schemes | `usr/share/color-schemes` |
| Vapor GTK 3 theme | `usr/share/themes/Vapor` |
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
- GTK 3: no startup warnings, no blank hovered partly-checked checkboxes.
  GTK 2 support dropped.
- Konsole and Alacritty: black is a visible dark grey instead of the background color.

## Install

Arch: AUR package `plasma6-themes-steamos-vapor-fixed`, or build it from
[aur/PKGBUILD](aur/PKGBUILD) with `makepkg -si`.

Manually, for your user only: copy the folders under `usr/share` into
`~/.local/share` (for example `usr/share/plasma/look-and-feel/*` into
`~/.local/share/plasma/look-and-feel/`). For the whole system, copy `usr/share`
into `/usr/share`.

Then pick a global theme in System Settings > Colors & Themes > Global Theme.

VGUI also uses the Plastik window decoration (`aurorae` package) and the
KDE_Classic cursor (`oxygen-cursors` package).

Alacritty: add the theme under `[general]` in `~/.config/alacritty/alacritty.toml`:

```toml
import = ["/usr/share/alacritty/themes/steamos-vapor.toml"]
```

## License

The theme files are Valve's, shipped by Valve under the GPL (GPL-2.0-or-later
per the package and global themes; the Vapor Plasma style's metadata says GPL
version 3). Steam, Steam Deck and their logos are trademarks of Valve
Corporation. This is an unofficial repackage, not affiliated with Valve.
