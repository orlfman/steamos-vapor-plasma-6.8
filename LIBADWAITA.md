# Vapor colors for libadwaita

Status: initial native compatibility profile, unreleased. Tested with libadwaita
1.10.0 and GTK 4.24.1. The existing 1.0.3 AUR release does not contain this feature.

The optional profile matches Vapor's dark surfaces and #569fcc accent with dark
#1f1f26 text. Adwaita keeps its widget shapes, spacing, responsive layouts and
semantic colors. It applies when the application uses dark appearance with
normal contrast; light and high-contrast appearances retain upstream colors.
It does not force an application's appearance preference.

## Try it from this checkout

Requires Python 3, GTK 4.24+ and libadwaita 1.10+. From the repository root:

```sh
python3 -I tools/vapor-libadwaita enable --dry-run
python3 -I tools/vapor-libadwaita enable
python3 -I tools/vapor-libadwaita status
```

Restart the GTK 4 applications you want to inspect. Choose dark appearance in
those applications or through the desktop's normal preference if needed.
After installation in a future package, the command is `vapor-libadwaita`.
No activation occurs merely by installing the files or selecting a global theme.

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
background watcher. `--config-home /absolute/test/config` and `--profile FILE`
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
GTK tests with the overlay, libadwaita, activation recovery and six deliberately
broken-profile checks:

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
```

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

It includes the existing theme/terminal files, profile, activation helper and
documentation. It does not install or activate them. For the next release,
update the AUR recipe/version/checksum and have its package function use the
staging tool (Python build dependency; optional Python/libadwaita runtime
requirements for activation). The current published recipe/tag/checksum remain
unchanged until that release is prepared. Flatpak integration remains a
separate milestone in [libadwaita-plan.md](libadwaita-plan.md).
