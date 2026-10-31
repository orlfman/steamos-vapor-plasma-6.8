#!/usr/bin/env python3
"""Prove GTK 3 VGUI2 palette, focus, bevel, artwork and behavior gates fail.

Mutations operate only on disposable copies, never the source or live theme.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'usr/share/themes/VGUI2Classic'


def main():
    cases=[
        ('wrong-gold','@define-color theme_selected_bg_color #958831;',
         '@define-color theme_selected_bg_color #569fcc;','GTK3-PALETTE:'),
        ('white-on-gold','@define-color theme_selected_fg_color #181810;',
         '@define-color theme_selected_fg_color #fcfcfc;','GTK3-PALETTE:'),
        ('dimmed-dark-text','@define-color theme_unfocused_selected_fg_color @theme_fg_color;',
         '@define-color theme_unfocused_selected_fg_color @theme_selected_fg_color;','GTK3-BACKDROP:'),
        ('wrong-window',None,'\n.background { background-color: #24272c; }\n','GTK3-SURFACE:'),
        ('weak-focus','@define-color vgui_focus #ffffe0;',
         '@define-color vgui_focus #958831;','GTK3-FOCUS:'),
        ('rounded-button',None,'\nbutton { border-radius: 8px; }\n','GTK3-BEVEL:'),
        ('blue-glyph',None,None,'GTK3-ARTWORK:'),
        ('lost-label-inheritance',None,None,'R1:'),
        ('horizontal-spin',None,'\nspinbutton:not(.vertical) button:backdrop:disabled { background-image: linear-gradient(to bottom, #000000, #ffffff); }\n','R2:'),
        ('vertical-spin',None,'\nspinbutton.vertical button:backdrop:disabled { background-image: linear-gradient(to bottom, #000000, #ffffff); }\n','R2:'),
        ('invalid-css',None,'\nbutton { vgui-invalid-property: 1; }\n','vgui-invalid-property'),
        ('missing-glyph',None,None,'Missing asset:'),
        ('missing-chooser',None,None,'Missing chooser entry'),
        ('hidden-rendered-glyphs',None,'\ncheck:checked, check:indeterminate, radio:checked, radio:indeterminate { -gtk-icon-source: none; }\n','GTK3-GLYPH:'),
        ('mixed-uses-checked',None,
         '\ncheck:indeterminate, radio:indeterminate { -gtk-icon-source: url("../assets/check.svg"); }\n','GTK3-GLYPH:'),
        ('inactive-warning',None,'\ninfobar.warning:backdrop { color: @warning_color; }\n','GTK3-STATES:'),
        ('inactive-error',None,'\ninfobar.error:backdrop { color: @error_color; }\n','GTK3-STATES:'),
        ('selected-nested-label',None,'\nrow:selected label, row:selected:backdrop label { color: @theme_selected_fg_color; }\n','GTK3-STATES:'),
        ('inactive-flow-label',None,'\nflowboxchild:selected:backdrop label { color: @theme_fg_color; }\n','GTK3-STATES:'),
        ('disabled-flow-label',None,'\nflowboxchild:selected:disabled label, flowboxchild:selected:disabled label:backdrop { color: @theme_selected_fg_color; }\n','GTK3-STATES:'),
        ('gold-focus',None,'\nbutton:focus:checked:not(:disabled) { outline-color: @vgui_focus; }\n','GTK3-FOCUS-STATES:'),
        ('iconview-focus',None,'\niconview:focus { outline-style: none; }\n','GTK3-FOCUS-STATES:'),
        ('vertical-arrows',None,'\nnotebook > header.left > tabs > arrow.down, notebook > header.right > tabs > arrow.down { -gtk-icon-source: -gtk-icontheme("pan-start-symbolic"); }\n','GTK3-NOTEBOOK:'),
    ]
    with tempfile.TemporaryDirectory(prefix='vgui2-gtk3-mutations-') as directory:
        root=Path(directory)
        for name,old,new,expected in cases:
            theme=root/name/'VGUI2Classic';shutil.copytree(SOURCE,theme)
            css=theme/'gtk-3.24/gtk.css';text=css.read_text()
            if name=='blue-glyph':
                path=theme/'assets/check.svg';path.write_text(path.read_text().replace('#181810','#569fcc'))
            elif name=='missing-glyph':(theme/'assets/check.svg').unlink()
            elif name=='missing-chooser':(theme/'gtk-3.0/gtk.css').unlink()
            elif name=='lost-label-inheritance':
                pattern=r'button:backdrop:checked:not\(:disabled\) label,\s*button:backdrop:active:not\(:disabled\) label\s*\{\s*color:\s*inherit;\s*\}'
                text,count=re.subn(pattern,'',text);assert count==1,count
            elif old is not None:
                assert text.count(old)==1,(name,'mutation missing');text=text.replace(old,new)
            else:text+=new
            css.write_text(text)
            result=subprocess.run([sys.executable,'-I',str(ROOT/'tools/check-gtk3.py'),
                                   '--family','vgui2','--theme',str(theme)],capture_output=True,text=True,timeout=35)
            exception='GLib.GError' if name=='invalid-css' else 'AssertionError'
            assert result.returncode and exception in result.stderr and expected in result.stderr,(
                name,result.returncode,result.stdout,result.stderr)
            print(f'VGUI2 GTK 3 rejected {name} ({expected})',flush=True)
    print(f'All {len(cases)} deliberate VGUI2 GTK 3 regressions rejected.')


if __name__=='__main__':main()
