#!/usr/bin/env python3
"""Stage the working tree's theme payload into an empty package directory.

Does not install anything, activate user CSS, build a release or update the AUR.
Includes the standard libadwaita profile, helper and Plasma login integration.
"""
import argparse
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destdir',required=True,type=Path)
    args=parser.parse_args()
    destination=args.destdir
    if not destination.is_absolute():parser.error('--destdir must be absolute')
    if destination.is_symlink():parser.error('Refusing a symlink destination')
    destination=destination.resolve()
    source=(ROOT/'usr').resolve()
    if destination.is_relative_to(source):
        parser.error('Destination must be outside the copied usr source tree')
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        parser.error('Destination must be an empty directory')
    destination.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source,destination/'usr',copy_function=shutil.copy2)
    def install(source,target,mode=0o644):
        target=destination/target;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/source,target);target.chmod(mode)
    install('alacritty/vapor.toml','usr/share/alacritty/themes/steamos-vapor.toml')
    install('kitty/vapor.conf','usr/share/kitty/themes/steamos-vapor.conf')
    install('libadwaita/vapor.css','usr/share/steamos-vapor/libadwaita/vapor.css')
    install('tools/vapor-libadwaita','usr/bin/vapor-libadwaita',0o755)
    install('autostart/steamos-vapor-libadwaita.desktop','etc/xdg/autostart/steamos-vapor-libadwaita.desktop')
    for name in ('README.md','CHANGES.txt','GTK3.md','gtk4port.md','LIBADWAITA.md','libadwaita-plan.md','audit.md',
                 'VGUI2-GTK3.md','vgui2-audit.md','vgui2-plan.md'):
        install(name,'usr/share/doc/plasma6-themes-steamos-vapor-fixed/'+name)
    for asset in ('docs/screenshots/vapor-libadwaita-mission-center-ffmpeg-converter-2026-10-30.png',
                  'docs/screenshots/vgui2-gtk3-preview.png','docs/screenshots/vgui2-gtk3-meld.png',
                  'docs/screenshots/vgui2-gtk3-states.png','docs/screenshots/vgui2-gtk3-notebooks.png',
                  'docs/screenshots/vgui2-qt-windows-reference.png','docs/audits/vgui2-feasibility.json',
                  'docs/audits/vgui2-gtk3-validation.json'):
        install(asset,'usr/share/doc/plasma6-themes-steamos-vapor-fixed/'+asset)
    print('Staged theme payload:',destination)


if __name__=='__main__':main()
