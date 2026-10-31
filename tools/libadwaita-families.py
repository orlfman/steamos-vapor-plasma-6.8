"""Independent libadwaita expectations anchored in the KDE/GTK family palettes."""
from pathlib import Path
import runpy

ROOT=Path(__file__).resolve().parent.parent
GTK=runpy.run_path(str(ROOT/'tools/theme-families.py'))


def get_family(name):
    family=GTK['get_family'](name)
    def hex_color(rgb):return ''.join(f'{value:02x}' for value in rgb)
    window=hex_color(family['window']);view=hex_color(family['view'])
    fg=hex_color(family['foreground']);accent=hex_color(family['selection'])
    accent_fg=hex_color(family['selection_foreground'])
    secondary,card=('282f21','56604e') if name=='vgui2' else ('1a212a','2d3136')
    colors={
        'accent-bg-color':accent,'accent-fg-color':accent_fg,
        'window-bg-color':window,'window-fg-color':fg,
        'view-bg-color':view,'view-fg-color':fg,
        'headerbar-bg-color':window,'headerbar-fg-color':fg,'headerbar-backdrop-color':window,
        'sidebar-bg-color':view,'sidebar-fg-color':fg,'sidebar-backdrop-color':secondary,
        'secondary-sidebar-bg-color':secondary,'secondary-sidebar-fg-color':fg,
        'secondary-sidebar-backdrop-color':window,'card-bg-color':card,'card-fg-color':fg,
        'dialog-bg-color':window,'dialog-fg-color':fg,'popover-bg-color':window,'popover-fg-color':fg,
        'thumbnail-bg-color':card,'thumbnail-fg-color':fg,'overview-bg-color':view,'overview-fg-color':fg,
        'active-toggle-bg-color':accent,'active-toggle-fg-color':accent_fg}
    if name=='vgui2':colors['accent-color']='ffffe0'
    family.update({'id':name,'colors':colors,'profile':ROOT/'libadwaita'/(name+'.css')})
    return family
