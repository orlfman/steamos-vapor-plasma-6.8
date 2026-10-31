# Vapor colors for libadwaita

Status: a standard installed component since 1.0.4. Tested with libadwaita
1.10.0 and GTK 4.24.1, plus successful user visual checks in Mission Center and
FFmpeg Converter GTK. Packages before 1.0.4 do not contain this feature.

Since **1.1.0**, the package also ships the [VGUI2 Classic profile](VGUI2-LIBADWAITA.md)
and automatically selects the matching family from the GTK theme.

The profile matches Vapor's dark surfaces and #569fcc accent with dark
#1f1f26 text. Adwaita keeps its widget shapes, spacing, responsive layouts and
semantic colors. It applies when the application uses dark appearance with
normal contrast; light and high-contrast appearances retain upstream colors.
It does not force an application's appearance preference.

## Activation

For everyday setup, follow the [numbered steps in the README](README.md#install).
You can select the theme in System Settings, save your work, then log out and
back in. The commands below are for optional controls, manual installation and
troubleshooting.

The package installs the profile, helper and a Plasma XDG autostart entry.
At each Plasma login, `vapor-libadwaita auto` reads the selected GTK theme from
the user's `gtk-4.0/settings.ini`, falling back to `gtk-3.0/settings.ini`. It
enables or refreshes the overlay for **Vapor** or **Vapor-dark**, chooses VGUI2 for **VGUI2Classic**, and removes
only its managed overlay if another theme is selected. Other users' existing
themes are left alone. The process exits after checking; there is no watcher.

Apply a changed theme selection immediately with `vapor-libadwaita auto`, then
restart GTK 4 applications. Choose dark appearance to see Vapor colors; light
and high-contrast appearances retain their original styling. The package build
and root package transaction do not modify any user's home directory.

## Use it from this checkout

Requires Python 3, GTK 4.24+ and libadwaita 1.10+. From the repository root:

```sh
python3 -I tools/vapor-libadwaita enable --dry-run
python3 -I tools/vapor-libadwaita enable
python3 -I tools/vapor-libadwaita status
```

Restart the GTK 4 applications you want to inspect. Choose dark appearance in
those applications or through the desktop's normal preference if needed.
With the package installed, the command is `vapor-libadwaita`.

The helper honors `XDG_CONFIG_HOME` (normally `~/.config`). It adds a marked
relative import to `gtk-4.0/gtk.css` and copies `vapor-libadwaita.css` beside it.
It retains the existing KDE `colors.css` import and all other content, saves an
original-file backup and records ownership/checksums in hidden sibling files.
Enable is idempotent and also refreshes an unedited profile copy after an update.

To remove the overlay:

```sh
python3 -I tools/vapor-libadwaita disable --dry-run
python3 -I tools/vapor-libadwaita disable
```

Disable also records a small `.vapor-libadwaita-disabled` preference beside the
GTK files, so future logins respect the choice. Enable clears that preference.
Dry runs change neither the overlay nor the preference. Disable before removing
the package if you want its user CSS removed as well.

Removal preserves unrelated CSS and edits made after activation. A missing
original `gtk.css` is removed again only if nothing else remains. Managed
profile edits, inconsistent backups, edited markers, symlinks, name collisions
and read-only files cause a refusal with an explanation instead of overwriting
or deleting the ambiguous content. Keep those files for recovery if this occurs.
The helper rolls back file contents/modes if an ordinary write operation fails;
this is not a guarantee against power loss, filesystem failure or another tool
editing the same files concurrently.

If KDE or another tool rewrites `gtk.css`, `status` reports the missing import.
Run enable again to reapply it while preserving the new file. There is no
background watcher. The next automatic login check also reapplies it when a supported GTK theme
is still selected and automatic activation has not been disabled.
`--config-home /absolute/test/config` and `--profile FILE`
allow isolated testing; `--json` produces machine-readable operation details.

## Scope and limits

Native GTK user CSS is shared by GTK 4 apps. It is not an app-specific theme
selection. The standard tests check that this profile preserves the existing
plain Vapor theme, including Widget Factory and inactive-label/spin fixes.

The layer is maintained by this project. Some applications use local colors,
hardcoded/custom drawing or the StyleManager accent API; those can still show
the original system accent. The overlay changes CSS variables rather than the
system accent API. Full Vapor widget geometry is not provided.

The automated fixtures cover native controls, sidebars, open Adw dialogs and
GTK menus/popovers, synthetic inactive/RTL/visible-focus states, light and
high-contrast baselines, dark/light transitions and integer scale 2. They do not
establish live GPU/Wayland, fractional scaling, every app-specific widget,
screen-reader support or comprehensive performance equivalence. The previous
4K/175% manual Widget Factory result covers plain GTK; repeat it with a real
libadwaita app before adding that claim here.

Flatpak support is not validated in this environment. Do not assume host
`/usr/share` imports work inside an app's runtime. Per-app activation needs
separate testing; this native helper changes no Flatpak permissions.

## Tests

Standard GTK 4 checks include native fixtures, Widget Factory, the same plain
GTK tests with the overlay, 22 libadwaita cases, 38 activation/recovery tests,
15 deliberately broken-profile checks and eight package-staging tests:

```sh
python3 -I tools/check-gtk4.py --output /tmp/vapor-all-gtk4
```

Additional requirements: the existing GTK 4 suite dependencies, installed
`libadwaita` with Adw GI data and Python 3. No browser dependency is added. A
small test-only client acknowledges the private Broadway display's protocol so
actual dialogs can complete their normal frame sequence. Native test rendering
uses Broadway; exported snapshots use Cairo. Nothing is sent to the desktop.

Targeted checks:

```sh
python3 -I tools/check-libadwaita.py --output /tmp/vapor-libadwaita
python3 -I tools/test-libadwaita-activation.py
python3 -I tools/test-libadwaita-regressions.py
python3 -I tools/test-package-staging.py
```

Surface checks rasterize the real window/header/card/view/sidebar/dialog/popover
CSS backgrounds over their ancestors and read the resulting pixels. Focus
contrast uses the actual adjacent background from the widget snapshot. Wrong
painted surfaces and a weak focus ring fail even when color variables are correct.
Activation tests cover malformed state flags without writing files and preserve
compatibility with older state files that omit the flag.
The same tests cover automatic theme selection, switching away/back, persistent
disable, dry runs, preference collisions and transactional rollback.

The two precise Broadway frame-timing warnings reproduced without the profile
are retained in reports; every other diagnostic fails. `check-libadwaita.py
--strict` rejects them too. The tests are not warning-free passes in strict mode.

Optional independent-application checks need a selected native app and a C
compiler/libadwaita development files; they do not download/install applications:

```sh
python3 -I tools/check-libadwaita-app.py \
  --application /absolute/path/to/adwaita-1-demo \
  --app-id org.gnome.Adwaita1.Demo --idle-seconds 2 \
  --output /tmp/vapor-adwaita-demo
```

This compares startup rendering/computed colors against an unmodified baseline.
An optional short idle CPU sample is an observation, not a performance guarantee.
No application actions or keyboard/mouse events are invoked.

## Packaging

Prepare an empty staging directory with:

```sh
python3 -I tools/stage-package.py --destdir /tmp/vapor-package-stage
```

It includes the existing theme/terminal files, profile, activation helper,
Plasma login entry, documentation and testing screenshot. Destinations inside
the copied `usr` source tree are rejected
before creating output, including paths through parent symlinks. An empty
repository `build/` directory outside `usr` is allowed.
Staging does not install or activate anything. The 1.0.4 AUR package uses this
tool for its full payload and requires Python, GTK 4.24+ and libadwaita 1.10+.
The installed login entry performs activation in the logged-in user's session.
Flatpak integration remains a separate milestone in
[libadwaita-plan.md](libadwaita-plan.md).

## Profile selection and upgrades since 1.1.0

`enable` follows the recognized GTK theme, falling back to legacy Vapor when no
supported GTK theme is selected. `enable --theme vgui2` or `--theme vapor` chooses
explicitly without changing the GTK setting; the next `auto` follows the actual
selection again. `status --json` reports active/selected profile IDs, pending
switches and updates relative to the active family. `--profile FILE` remains a
diagnostic override, including with auto.

Legacy schema-1 state is recognized as Vapor. New state adds a validated
`profile_id` while keeping the original import, filenames and backup. A family
swap updates the owned CSS/state together, leaving original and later user CSS
intact. Unknown IDs and local edits are refused. Explicit disable remains shared
across both families until enable clears it. Package installation does not write
user homes; existing users get the selection at login or via `vapor-libadwaita
auto`, then restart GTK 4 apps. Neither the GTK theme nor app appearance is forced.
