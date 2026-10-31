#!/usr/bin/env python3
"""Reject deliberate VGUI2 GTK 4 faults using only disposable theme copies."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'usr/share/themes/VGUI2Classic'


def main():
    cases=[
        ('wrong-gold','@define-color theme_selected_bg_color #958831;',
         '@define-color theme_selected_bg_color #569fcc;','GTK4-PALETTE:',()),
        ('white-on-gold','@define-color theme_selected_fg_color #181810;',
         '@define-color theme_selected_fg_color #fcfcfc;','GTK4-PALETTE:',()),
        ('wrong-window',None,'\n.background, .background:backdrop { background-color: #24272c; }\n','GTK4-SURFACE:',()),
        ('nested-button-label',None,'\nrow:selected label { color: @theme_selected_fg_color; }\n','GTK4-LABELS:',()),
        ('inactive-flow-label',None,'\nflowboxchild:selected:backdrop label { color: @theme_fg_color; }\n','GTK4-LABELS:',('--state','backdrop')),
        ('inactive-listview-label',None,'\nlistview > row.activatable:selected:backdrop label { color: @theme_fg_color; }\n','GTK4-LABELS:',('--state','backdrop')),
        ('inactive-warning',None,'\ninfobar.warning:backdrop { color: @warning_color; }\n','GTK4-LABELS:',('--state','backdrop')),
        ('inactive-error',None,'\ninfobar.error:backdrop { color: @error_color; }\n','GTK4-LABELS:',('--state','backdrop')),
        ('hidden-glyphs',None,'\ncheck:checked, check:indeterminate, radio:checked, radio:indeterminate { -gtk-icon-source: none; }\n','GTK4-GLYPH:',()),
        ('mixed-as-checked',None,'\ncheck:indeterminate { -gtk-icon-source: url("../assets/check.svg"); }\n','GTK4-GLYPH:',()),
        ('missing-focus',None,'\nbutton:focus { outline-style: none; }\n','GTK4-FOCUS:',()),
        ('gold-focus',None,'\nbutton:focus:checked:not(:disabled) { outline-color: @theme_selected_bg_color; }\n','GTK4-FOCUS:',()),
        ('vertical-arrows',None,'\nnotebook > header.left > tabs > arrow.down { background-image: -gtk-icontheme("pan-start-symbolic"); }\n','GTK4-NOTEBOOK:',()),
        ('menu-label',None,'\npopover.menu modelbutton.flat:hover label { color: @theme_fg_color; }\n','GTK4-POPUP:',()),
        ('invalid-css',None,'\nbutton { vgui-invalid-property: 1; }\n','GTK4-CSS:',()),
        ('missing-asset',None,None,'GTK4-ASSET:',()),
        ('missing-dark-entry',None,None,'GTK4-ENTRY:',()),
        ('horizontal-spin',None,'\nspinbutton:not(.vertical) button:backdrop:disabled { background-image: linear-gradient(to bottom,#000000,#ffffff); }\n','R2:',('behavior',)),
        ('vertical-spin',None,'\nspinbutton.vertical button:backdrop:disabled { background-image: linear-gradient(to bottom,#000000,#ffffff); }\n','R2:',('behavior',)),
    ]
    with tempfile.TemporaryDirectory(prefix='vgui2-gtk4-mutations-') as name:
        root=Path(name);reports=[]
        for name,old,new,expected,options in cases:
            theme=root/name/'VGUI2Classic';shutil.copytree(SOURCE,theme)
            css=theme/'gtk-4.0/gtk.css';text=css.read_text()
            if name=='missing-asset':(theme/'assets/check.svg').unlink()
            elif name=='missing-dark-entry':(theme/'gtk-4.0/gtk-dark.css').unlink()
            elif old is not None:
                assert text.count(old)==1,(name,'mutation missing');text=text.replace(old,new)
            else:text+=new
            css.write_text(text)
            if options==('behavior',):
                command=[sys.executable,'-I',str(ROOT/'tools/check-gtk-regressions.py'),
                         '--gtk','4.0','--family','vgui2','--theme',str(theme)]
            else:
                command=[sys.executable,'-I',str(ROOT/'tools/check-vgui2-gtk4.py'),
                         '--quick','--theme',str(theme),*options]
            result=subprocess.run(command,capture_output=True,text=True,timeout=30)
            assert result.returncode and 'AssertionError' in result.stderr and expected in result.stderr,(
                name,result.returncode,result.stdout,result.stderr)
            reports.append({'mutation':name,'gate':expected,'rejected':True})
            print(f'VGUI2 GTK 4 rejected {name} ({expected})',flush=True)
    print(f'All {len(reports)} deliberate VGUI2 GTK 4 regressions rejected.')


if __name__=='__main__':main()
