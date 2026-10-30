#!/usr/bin/env python3
"""Prove GTK behavior checks reject each deliberately reverted R1/R2 fix.

No working-tree theme is modified. Requires the same GTK 3/4 test dependencies
as check-gtk3.py/check-gtk4.py. All mutated copies live in disposable /tmp data.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent


def main():
    with tempfile.TemporaryDirectory(prefix='vapor-gtk-mutations-') as name:
        scratch=Path(name)
        for gtk,version in (('3.0','gtk-3.24'),('4.0','gtk-4.0')):
            for defect in ('label','horizontal-spin','vertical-spin'):
                theme=scratch/f'{gtk}-{defect}'/'Vapor'
                shutil.copytree(ROOT/'usr/share/themes/Vapor',theme)
                path=theme/version/'gtk.css'
                text=path.read_text()
                if defect=='label':
                    pattern=r'button:backdrop:checked:not\(:disabled\) label,\s*button:backdrop:active:not\(:disabled\) label\s*\{\s*color:\s*inherit;\s*\}'
                    text,count=re.subn(pattern,'',text)
                    expected='R1:'
                else:
                    orientation=r':not\(\.vertical\)' if defect=='horizontal-spin' else r'\.vertical'
                    pattern=r'(spinbutton'+orientation+r' button:backdrop:disabled\s*\{[^{}]*?)\s*background-image:\s*none;'
                    text,count=re.subn(pattern,lambda m:m[1],text)
                    expected='R2:'
                assert count==1,(gtk,defect,count)
                path.write_text(text)
                result=subprocess.run([sys.executable,'-I',str(ROOT/'tools/check-gtk-regressions.py'),
                                       '--gtk',gtk,'--theme',str(theme)],capture_output=True,text=True,timeout=30)
                assert result.returncode!=0 and ('AssertionError: '+expected) in result.stderr,(gtk,defect,result.stdout,result.stderr)
                print(f'GTK {gtk}: rejected reverted {defect} fix ({expected[:-1]})')
    print('All six deliberate regressions rejected; working-tree styles untouched.')


if __name__=='__main__':main()
