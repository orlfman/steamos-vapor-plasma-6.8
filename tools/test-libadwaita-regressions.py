#!/usr/bin/env python3
"""Prove color, guard, actual-surface and focus regressions fail on private copies."""
from pathlib import Path
import argparse
import runpy
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family',choices=('vapor','vgui2'),default='vapor')
    args=parser.parse_args()
    family=runpy.run_path(str(ROOT/'tools/libadwaita-families.py'))['get_family'](args.family)
    original=family['profile'].read_text()
    accent=family['colors']['accent-bg-color'];foreground=family['colors']['accent-fg-color']
    def guarded(rule):
        return '\n@media (prefers-color-scheme: dark) and (prefers-contrast: no-preference) {\n'+rule+'\n}\n'
    cases=[
        ('wrong-accent','--accent-bg-color: #'+accent+';','--accent-bg-color: #3daee9;',['--quick'],'ADW-COLOR: accent-bg-color'),
        ('wrong-foreground','--accent-fg-color: #'+foreground+';','--accent-fg-color: #ffffff;',['--quick'],'ADW-COLOR: accent-fg-color'),
        ('missing-import',None,None,['--quick','--without-import'],'ADW-COLOR: accent-bg-color'),
        ('missing-dark-guard','(prefers-color-scheme: dark) and (prefers-contrast: no-preference)',
         '(prefers-contrast: no-preference)',['--light'],'ADW-GUARD:'),
        ('missing-contrast-guard','(prefers-color-scheme: dark) and (prefers-contrast: no-preference)',
         '(prefers-color-scheme: dark)',['--hc'],'ADW-GUARD:'),
        ('invalid-css',None,'\nbutton { vapor-invalid-property: 1; }\n',['--quick'],'ADW-CSS:'),
        ('wrong-window-grey',None,guarded('window { background-color: #555555; }'),['--quick'],'ADW-SURFACE: window'),
        ('wrong-window-green',None,guarded('window { background-color: #29362f; }'),['--quick'],'ADW-SURFACE: window'),
        ('wrong-header',None,guarded('headerbar { background-color: #555555; }'),['--quick'],'ADW-SURFACE: headerbar'),
        ('wrong-card',None,guarded('.vapor-fixture-card { background-color: #555555; }'),['--quick'],'ADW-SURFACE: card'),
        ('wrong-view',None,guarded('textview.view, textview.view text { background-color: #555555; }'),['--quick'],'ADW-SURFACE: view'),
        ('wrong-sidebar',None,guarded('.vapor-fixture-sidebar { background-color: #555555; }'),['--scene','sidebar'],'ADW-SURFACE: sidebar'),
        ('wrong-dialog',None,guarded('.vapor-fixture-dialog { background-color: #555555; }'),['--scene','dialog'],'ADW-SURFACE: dialog'),
        ('wrong-popover',None,guarded('.vapor-fixture-popup { background-color: #555555; }'),['--scene','popover'],'ADW-SURFACE: popover'),
        ('weak-local-focus',None,guarded('.vapor-fixture-actions { background-color: #'+('888888' if args.family=='vgui2' else '555555')+'; }'),['--state','focus'],'ADW-FOCUS: weak ring')]
    if args.family=='vgui2':
        cases += [
            ('weak-card-focus','--vgui2-button-focus-coverage: 65%;','--vgui2-button-focus-coverage: 50%;',['--state','focus-card'],'ADW-FOCUS: weak ring'),
            ('wrong-standalone','--accent-color: #ffffe0;','--accent-color: #958831;',['--quick'],'ADW-COLOR: accent-color'),
        ]
    with tempfile.TemporaryDirectory(prefix='vapor-adw-mutations-') as folder:
        scratch=Path(folder)
        for name,old,new,options,expected in cases:
            text=original
            if old:
                assert text.count(old)==1,(name,old)
                text=text.replace(old,new)
            elif new:text+=new
            profile=scratch/(name+'.css');profile.write_text(text)
            result=subprocess.run([sys.executable,'-I',str(ROOT/'tools/check-libadwaita.py'),
                                   '--family',args.family,'--profile',str(profile),*options],capture_output=True,text=True,timeout=35)
            assert result.returncode!=0 and ('AssertionError: '+expected) in result.stderr,(name,result.stdout,result.stderr)
            print(f'Libadwaita: rejected {name} ({expected})',flush=True)
        if args.family=='vgui2':
            controls=[
                ('weak-checked-focus',None,guarded('button.toggle:checked:focus:focus-visible:not(.suggested-action):not(.opaque):not(.arrow-button):not(.osd):not(.link):not(:disabled) { outline-color: color-mix(in srgb, var(--accent-color) 65%, transparent); }'),['--quick'],'ADW-CONTROL-FOCUS:'),
                ('unreadable-checked-text',None,guarded('button.toggle:checked:not(.suggested-action):not(.opaque):not(.arrow-button):not(.osd):not(.link):not(:disabled) label:not(.error):not(.warning):not(.success):not(.accent) { color: var(--window-fg-color); }'),['--quick'],'ADW-CONTROL-TEXT:'),
                ('unreadable-ordinary-activation',None,guarded('button:active:not(.suggested-action):not(.opaque):not(.arrow-button):not(.osd):not(.link):not(:disabled) label:not(.error):not(.warning):not(.success):not(.accent) { color: var(--window-fg-color); }'),['--quick'],'ADW-CONTROL-TEXT:'),
                ('weak-input-focus','--vgui2-control-focus-coverage: 80%;','--vgui2-control-focus-coverage: 50%;',['--quick'],'ADW-CONTROL-FOCUS:'),
                ('semantic-parent-focus','.destructive-action, .error, .warning, .success','.error, .warning, .success',['--quick'],'ADW-CONTROL-SEMANTIC:'),
                ('changed-check-geometry',None,guarded('checkbutton { min-height: 80px; }'),['--quick'],'ADW-CONTROL-GEOMETRY:'),
                ('unguarded-light-focus',None,'\n@media (prefers-color-scheme: light) { button:focus:focus-visible { outline-color: red; } }\n',['--light'],'ADW-CONTROL-GUARD:'),
            ]
            for name,old,new,options,expected in controls:
                assert old is None or original.count(old)==1,(name,old)
                text=original.replace(old,new) if old else original+new
                profile=scratch/(name+'.css');profile.write_text(text)
                result=subprocess.run([sys.executable,'-I',str(ROOT/'tools/check-vgui2-libadwaita.py'),
                                       '--profile',str(profile),*options],capture_output=True,text=True,timeout=35)
                assert result.returncode!=0 and ('AssertionError: '+expected) in result.stderr,(name,result.stdout,result.stderr)
                print(f'Libadwaita: rejected {name} ({expected})',flush=True)
            cases += controls
            theme=scratch/'VGUI2Classic'
            shutil.copytree(ROOT/'usr/share/themes/VGUI2Classic',theme)
            css=theme/'gtk-4.0/gtk.css'
            text=css.read_text();assert '--vgui2-classic-focus-color:' in text
            css.write_text(''.join(line for line in text.splitlines(keepends=True)
                                   if '--vgui2-classic-focus-color:' not in line))
            result=subprocess.run([sys.executable,'-I',str(ROOT/'tools/check-vgui2-gtk4.py'),
                                   '--theme',str(theme),'--user-css',str(family['profile']),
                                   '--quick','--dark'],capture_output=True,text=True,timeout=35)
            assert result.returncode!=0 and 'AssertionError: GTK4-FOCUS:' in result.stderr,('missing-classic-focus-bridge',result.stdout,result.stderr)
            print('Libadwaita: rejected missing-classic-focus-bridge (GTK4-FOCUS:)',flush=True)
            cases.append(('missing-classic-focus-bridge',))
    print(f'All {len(cases)} deliberate libadwaita regressions rejected; source profile unchanged.')


if __name__=='__main__':main()
