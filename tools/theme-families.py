"""Independent expected palettes for the GTK test fixtures, anchored in KDE schemes."""
import configparser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAMILIES = {
    'vapor': {'name': 'Vapor', 'scheme': 'Vapor.colors',
              'selection_scheme': 'Vapor.colors', 'assets': 'png', 'classic': False},
    'vgui2': {'name': 'VGUI2Classic', 'scheme': 'VGUI.colors',
              'selection_scheme': 'VGUIUnion.colors', 'assets': 'svg', 'classic': True,
              'focus': (255, 255, 224), 'link': (240, 224, 120)},
}


def get_family(name):
    result = dict(FAMILIES[name])
    scheme = configparser.ConfigParser(interpolation=None)
    scheme.read(ROOT/'usr/share/color-schemes'/result['scheme'])
    selection = configparser.ConfigParser(interpolation=None)
    selection.read(ROOT/'usr/share/color-schemes'/result['selection_scheme'])

    def color(parser, section, key):
        return tuple(int(value) for value in parser[section][key].split(','))

    result.update({
        # Ordinary GTK control text matches Button, not Window (Vapor differs).
        'foreground': color(scheme, 'Colors:Button', 'ForegroundNormal'),
        'window': color(scheme, 'Colors:Window', 'BackgroundNormal'),
        'view': color(scheme, 'Colors:View', 'BackgroundNormal'),
        'selection': color(scheme, 'Colors:Selection', 'BackgroundNormal'),
        'selection_foreground': color(selection, 'Colors:Selection', 'ForegroundNormal'),
    })
    return result
