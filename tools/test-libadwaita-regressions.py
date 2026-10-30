#!/usr/bin/env python3
"""Prove color, guard, actual-surface and focus regressions fail on private copies."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent


def main():
    original=(ROOT/'libadwaita/vapor.css').read_text()
    def guarded(rule):
        return '\n@media (prefers-color-scheme: dark) and (prefers-contrast: no-preference) {\n'+rule+'\n}\n'
    cases=[
        ('wrong-blue','--accent-bg-color: #569fcc;','--accent-bg-color: #3daee9;',['--quick'],'ADW-COLOR: accent-bg-color'),
        ('wrong-foreground','--accent-fg-color: #1f1f26;','--accent-fg-color: #ffffff;',['--quick'],'ADW-COLOR: accent-fg-color'),
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
        ('weak-local-focus',None,guarded('.vapor-fixture-actions { background-color: #555555; }'),['--state','focus'],'ADW-FOCUS: weak ring')]
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
                                   '--profile',str(profile),*options],capture_output=True,text=True,timeout=35)
            assert result.returncode!=0 and ('AssertionError: '+expected) in result.stderr,(name,result.stdout,result.stderr)
            print(f'Libadwaita: rejected {name} ({expected})',flush=True)
    print(f'All {len(cases)} deliberate libadwaita regressions rejected; source profile unchanged.')


if __name__=='__main__':main()
