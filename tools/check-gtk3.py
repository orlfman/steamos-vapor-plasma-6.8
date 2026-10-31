#!/usr/bin/env python3
"""Check Vapor and VGUI2 Classic CSS, discovery and rendering with GTK 3.24.

Uses temporary XDG settings and a private Broadway server over Unix sockets.
Requires python-gobject, pycairo, Pillow, gtk3/broadwayd, librsvg, D-Bus and fonts.
No installed theme or desktop settings are modified. Optional PNGs go to --output.
"""
import argparse
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
FAMILY_TOOLS = runpy.run_path(str(ROOT/'tools/theme-families.py'))


def worker(args):
    import warnings
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    assert Gtk.get_major_version() == 3 and Gtk.get_minor_version() >= 24
    theme = Path(args.theme)
    family = FAMILY_TOOLS['get_family'](args.family)
    errors = []
    providers = []
    for css in sorted(theme.glob('gtk-3*/*.css')):
        if args.baseline and css.parent.name != 'gtk-3.20':
            continue
        provider = Gtk.CssProvider()
        provider.connect('parsing-error', lambda _p, s, e: errors.append(
            f'{s.get_file().get_path()}:{s.get_start_line()+1}: {e.message}'))
        provider.load_from_path(str(css))
        providers.append(provider)
    assert not errors, '\n'.join(errors)
    # Prove the named loader selected this staged theme, not installed Vapor.
    # The parent adds an unused named color only to its temporary fixture copy.
    provider = Gtk.CssProvider.get_named(family['name'], None)
    serialized = provider.to_string()
    assert '@define-color vapor_test_fixture rgb(17,23,29);' in serialized, 'Named loader used another theme'
    for dark in (False, True):
        named = Gtk.CssProvider.get_named(family['name'], 'dark' if dark else None)
        assert named.to_string() == serialized, 'Unexpected dark variant fallback'

    def node_context(root_type, names, root_classes=(), state=Gtk.StateFlags.NORMAL):
        path = Gtk.WidgetPath.new()
        for i, name in enumerate(names):
            index = path.append_type(root_type if i == 0 else Gtk.Widget)
            path.iter_set_object_name(index, name)
            path.iter_set_state(index, state)
            if i == 0:
                for cls in root_classes:
                    path.iter_add_class(index, cls)
        context = Gtk.StyleContext.new()
        context.set_path(path)
        context.set_state(state)
        context.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_THEME)
        return context

    selection = node_context(Gtk.Label, ['label', 'selection'], state=Gtk.StateFlags.BACKDROP)
    color = selection.get_background_color(Gtk.StateFlags.BACKDROP)
    selection_rgba = [round(v, 5) for v in (color.red, color.green, color.blue, color.alpha)]
    fine = node_context(Gtk.Scale, ['scale', 'contents', 'trough'], ('fine-tune', 'horizontal'))
    fine_margin = fine.get_margin(Gtk.StateFlags.NORMAL).left
    if not args.baseline:
        assert selection_rgba == [round(v, 5) for v in (*[c/255 for c in family['selection']], .5)], ('GTK3-PALETTE:',selection_rgba)
        # Kept as upstream Breeze GTK has it: the scale.fine-tune.trough rule never
        # matches, so a slider keeps its 9px trough margin (and size) while GTK's
        # fine-tune (zoom) drag is active instead of shrinking by 2px mid-drag.
        assert fine_margin == 9, fine_margin

    if not args.baseline:
        expected_bg = [n/255 for n in family['selection']]
        expected_fg = [n/255 for n in family['selection_foreground']]
        for widget_type, names, flags in (
                (Gtk.Label, ['label', 'selection'], Gtk.StateFlags.NORMAL),
                (Gtk.Entry, ['entry', 'selection'], Gtk.StateFlags.NORMAL),
                (Gtk.ListBox, ['list', 'row'], Gtk.StateFlags.SELECTED),
                (Gtk.TreeView, ['treeview'], Gtk.StateFlags.SELECTED)):
            context = node_context(widget_type, names, ('view',) if widget_type == Gtk.TreeView else (), flags)
            background = context.get_background_color(flags)
            foreground = context.get_color(flags)
            assert [round(v, 5) for v in (background.red, background.green, background.blue)] == [round(v, 5) for v in expected_bg], ('GTK3-PALETTE:', names)
            assert [round(v, 5) for v in (foreground.red, foreground.green, foreground.blue)] == [round(v, 5) for v in expected_fg], ('GTK3-PALETTE:', names, foreground.to_string())
        assert '#3daee9' not in (theme/'gtk-3.24/gtk.css').read_text().lower()
        if family['classic']:
            assert '#569fcc' not in (theme/'gtk-3.24/gtk.css').read_text().lower(), 'GTK3-PALETTE: Vapor blue leaked'
        # Unfocused (backdrop) selections must stay readable. Dimmed selections are
        # drawn at half strength over the view and need light text; activatable rows
        # (list boxes, places sidebar) stay full strength and need the dark text.
        def luminance(rgb):
            return sum(w * (v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4)
                       for w, v in zip((0.2126, 0.7152, 0.0722), rgb))

        def contrast(a, b):
            la, lb = sorted((luminance(a), luminance(b)), reverse=True)
            return (la + 0.05) / (lb + 0.05)

        def over(rgba, under):
            return [c * rgba.alpha + u * (1 - rgba.alpha)
                    for c, u in zip((rgba.red, rgba.green, rgba.blue), under)]

        view = node_context(Gtk.TreeView, ['treeview'], ('view',))
        view_bg = view.get_background_color(Gtk.StateFlags.NORMAL)
        view_rgb = [view_bg.red, view_bg.green, view_bg.blue]
        backdrop = Gtk.StateFlags.BACKDROP
        for widget_type, names, classes, flags in (
                (Gtk.TreeView, ['treeview'], ('view',), Gtk.StateFlags.SELECTED | backdrop),
                (Gtk.TextView, ['textview', 'text', 'selection'], ('view',), backdrop),
                (Gtk.Entry, ['entry', 'selection'], (), backdrop)):
            context = node_context(widget_type, names, classes, flags)
            background = over(context.get_background_color(flags), view_rgb)
            foreground = over(context.get_color(flags), background)
            ratio = contrast(foreground, background)
            assert ratio >= 4.5, ('GTK3-BACKDROP:', names, round(ratio, 2))

        path = Gtk.WidgetPath.new()
        state = Gtk.StateFlags.SELECTED | backdrop
        for index, (gtype, name, classes) in enumerate(((Gtk.ListBox, 'list', ()),
                                                        (Gtk.ListBoxRow, 'row', ('activatable',)),
                                                        (Gtk.Label, 'label', ()))):
            path.append_type(gtype)
            path.iter_set_object_name(index, name)
            path.iter_set_state(index, state)
            for cls in classes:
                path.iter_add_class(index, cls)
        row_label = Gtk.StyleContext.new()
        row_label.set_path(path)
        row_label.set_state(state)
        row_label.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_THEME)
        label_fg = row_label.get_color(state)
        ratio = contrast([label_fg.red, label_fg.green, label_fg.blue], expected_bg)
        assert ratio >= 4.5, ('activatable row label, backdrop', round(ratio, 2))
        ordinary = node_context(Gtk.Button, ['button'])
        fg = ordinary.get_color(Gtk.StateFlags.NORMAL)
        assert tuple(round(v*255) for v in (fg.red, fg.green, fg.blue)) == family['foreground']
        gi.require_version('GdkPixbuf', '2.0')
        from gi.repository import GdkPixbuf
        accent_pixels = 0
        expected_art = family['selection_foreground'] if family['assets']=='svg' else family['selection']
        for image in (theme/'assets').glob('*.'+family['assets']):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(image))
            pixels = pixbuf.get_pixels()
            stride, channels = pixbuf.get_rowstride(), pixbuf.get_n_channels()
            for y in range(pixbuf.get_height()):
                for x in range(pixbuf.get_width()):
                    i = y * stride + x * channels
                    if channels == 4 and pixels[i+3] == 0:
                        continue
                    rgb = tuple(pixels[i:i+3])
                    assert rgb != (61, 174, 233), f'Old solid blue in {image.name}'
                    if family['classic']:
                        assert rgb != (86,159,204), 'GTK3-ARTWORK: Vapor blue in '+image.name
                    accent_pixels += rgb == expected_art
        assert accent_pixels > 0, 'GTK3-ARTWORK: missing expected indicator color'


    # Broadway has a scale-1 display. Exercise @2 artwork separately through
    # GTK's scaled style contexts and Cairo, without claiming a scale-2 window.
    import cairo
    indicator_results = []
    for scale_factor in (1, 2):
        for name, draw in (('check', Gtk.render_check), ('radio', Gtk.render_option)):
            for state_name, flags in (('checked', Gtk.StateFlags.CHECKED),
                                      ('mixed-hover', Gtk.StateFlags.INCONSISTENT | Gtk.StateFlags.PRELIGHT)):
                context = node_context(Gtk.ModelButton, ['modelbutton', name], ('flat',), flags)
                context.set_scale(scale_factor)
                surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 24 * scale_factor, 24 * scale_factor)
                cr = cairo.Context(surface)
                cr.scale(scale_factor, scale_factor)
                if family['classic']:
                    Gtk.render_background(context, cr, 2, 2, 20, 20)
                    Gtk.render_frame(context, cr, 2, 2, 20, 20)
                draw(context, cr, 2, 2, 20, 20)
                surface.flush()
                assert any(surface.get_data()), f'Blank {name} {state_name} at {scale_factor}x'
                surface.write_to_png(str(Path(args.output) / f'indicator-{name}-{state_name}-{scale_factor}x.png'))
                indicator_results.append(f'{name}-{state_name}-{scale_factor}x')

    classic_checks = {}
    if family['classic']:
        from PIL import Image

        def painted(name, widget_type, nodes, flags=Gtk.StateFlags.NORMAL, classes=(), focus=False, backdrop=None):
            context=node_context(widget_type,nodes,classes,flags)
            surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,100,38)
            cr=cairo.Context(surface)
            if backdrop:
                cr.set_source_rgb(*[v/255 for v in backdrop]);cr.paint()
            Gtk.render_background(context,cr,0,0,100,38)
            Gtk.render_frame(context,cr,0,0,100,38)
            if focus:Gtk.render_focus(context,cr,0,0,100,38)
            path=Path(args.output)/('classic-'+name+'.png');surface.write_to_png(str(path))
            with Image.open(path) as capture:image=capture.convert('RGBA')
            return context,image

        context,normal=painted('button',Gtk.Button,['button'])
        assert normal.getpixel((50,19))[:3]==family['window'],'GTK3-SURFACE: normal button'
        corners=[normal.getpixel(p) for p in ((0,0),(99,0),(0,37),(99,37))]
        assert all(p[3]==255 for p in corners),'GTK3-BEVEL: rounded or transparent button corners'
        assert normal.getpixel((50,0))!=normal.getpixel((50,37)),'GTK3-BEVEL: raised edges missing'
        foreground=context.get_color(Gtk.StateFlags.NORMAL)
        ratio=contrast([foreground.red,foreground.green,foreground.blue],
                       [v/255 for v in normal.getpixel((50,19))[:3]])
        assert ratio>=4.5,'GTK3-CONTRAST: ordinary text'
        classic_checks['ordinary']=round(ratio,3)
        secondary=node_context(Gtk.Label,['label'],('dim-label',)).get_color(Gtk.StateFlags.NORMAL)
        ratio=contrast([secondary.red,secondary.green,secondary.blue],[v/255 for v in family['window']])
        assert ratio>=4.5,'GTK3-CONTRAST: secondary text'
        classic_checks['secondary']=round(ratio,3)
        state=Gtk.StateFlags.SELECTED|Gtk.StateFlags.INSENSITIVE|Gtk.StateFlags.BACKDROP
        disabled_row=node_context(Gtk.ListBox,['list','row','label'],state=state).get_color(state)
        assert disabled_row.alpha<1,'GTK3-DISABLED: selected row label lost dimming'
        assert tuple(round(v*255) for v in (disabled_row.red,disabled_row.green,disabled_row.blue))!=family['selection_foreground'],'GTK3-DISABLED: selected row retained enabled text'
        for name,flags,classes in (
                ('checked',Gtk.StateFlags.CHECKED,()),
                ('pressed',Gtk.StateFlags.ACTIVE,()),
                ('checked-backdrop',Gtk.StateFlags.CHECKED|Gtk.StateFlags.BACKDROP,()),
                ('suggested',Gtk.StateFlags.NORMAL,('suggested-action',))):
            context,image=painted(name,Gtk.Button,['button'],flags,classes)
            background=image.getpixel((50,19))[:3]
            foreground=context.get_color(flags)
            actual=[foreground.red,foreground.green,foreground.blue]
            ratio=contrast(actual,[v/255 for v in background])
            assert background==family['selection'],'GTK3-PALETTE: '+name
            assert ratio>=4.5,f'GTK3-CONTRAST: {name}: {ratio}'
            classic_checks[name]=round(ratio,3)
        context,image=painted('entry',Gtk.Entry,['entry'])
        assert image.getpixel((50,19))[:3]==family['view'],'GTK3-SURFACE: entry'
        foreground=context.get_color(Gtk.StateFlags.NORMAL)
        ratio=contrast([foreground.red,foreground.green,foreground.blue],
                       [v/255 for v in image.getpixel((50,19))[:3]])
        assert ratio>=4.5,'GTK3-CONTRAST: entry text'
        classic_checks['entry']=round(ratio,3)
        context,image=painted('tooltip',Gtk.Window,['tooltip'],classes=('background',))
        background=image.getpixel((50,19))[:3];foreground=context.get_color(Gtk.StateFlags.NORMAL)
        assert background==family['window'],'GTK3-SURFACE: tooltip'
        ratio=contrast([foreground.red,foreground.green,foreground.blue],[v/255 for v in background])
        assert ratio>=4.5,'GTK3-CONTRAST: tooltip text'
        classic_checks['tooltip']=round(ratio,3)
        context,image=painted('destructive',Gtk.Button,['button'],classes=('destructive-action',))
        background=image.getpixel((50,19))[:3];foreground=context.get_color(Gtk.StateFlags.NORMAL)
        ratio=contrast([foreground.red,foreground.green,foreground.blue],[v/255 for v in background])
        assert background[0]>background[1] and ratio>=4.5,'GTK3-CONTRAST: destructive action'
        classic_checks['destructive']=round(ratio,3)
        for state in (Gtk.StateFlags.LINK,Gtk.StateFlags.LINK|Gtk.StateFlags.BACKDROP):
            context=node_context(Gtk.LinkButton,['button'],state=state)
            color=context.get_color(state)
            ratio=contrast([color.red,color.green,color.blue],[v/255 for v in family['window']])
            assert ratio>=4.5,'GTK3-CONTRAST: link'
            classic_checks['link']=round(ratio,3)
        context,focused=painted('focus',Gtk.Button,['button'],Gtk.StateFlags.FOCUSED,focus=True)
        changed=[focused.getpixel((x,y)) for y in range(38) for x in range(100)
                 if focused.getpixel((x,y))!=normal.getpixel((x,y))]
        assert changed,'GTK3-FOCUS: no painted ring'
        background=normal.getpixel((50,19))[:3]
        ratio=max(contrast([v/255 for v in p[:3]],[v/255 for v in background]) for p in changed)
        assert ratio>=3,f'GTK3-FOCUS: weak ring {ratio}'
        classic_checks['focus']=round(ratio,3)
        for name,kind,nodes,classes,parent_color in (
                ('row',Gtk.ListBox,['list','row'],(),family['view']),
                ('tab',Gtk.Notebook,['notebook','header','tabs','tab'],(),family['window']),
                ('modelbutton',Gtk.ModelButton,['modelbutton'],('flat',),family['window']),
                ('entry',Gtk.Entry,['entry'],(),family['window']),
                ('checkbutton',Gtk.CheckButton,['checkbutton'],(),family['window']),
                ('switch',Gtk.Switch,['switch'],(),family['window'])):
            _,base=painted(name+'-base',kind,nodes,classes=classes,backdrop=parent_color)
            _,image=painted(name+'-focus',kind,nodes,Gtk.StateFlags.FOCUSED,classes,True,parent_color)
            changed=[(x,y) for y in range(38) for x in range(100) if image.getpixel((x,y))!=base.getpixel((x,y))]
            assert changed,'GTK3-FOCUS: no '+name+' ring'
            ratio=max(contrast([v/255 for v in image.getpixel(p)[:3]],
                               [v/255 for v in base.getpixel(p)[:3]]) for p in changed)
            assert ratio>=3,f'GTK3-FOCUS: weak {name} ring {ratio}'
            classic_checks['focus-'+name]=round(ratio,3)
        _,trough=painted('progress-trough',Gtk.ProgressBar,['progressbar','trough'])
        _,fill=painted('progress-fill',Gtk.ProgressBar,['progressbar','trough','progress'])
        ratio=contrast([v/255 for v in fill.getpixel((50,19))[:3]],
                       [v/255 for v in trough.getpixel((50,19))[:3]])
        assert ratio>=3,f'GTK3-CONTRAST: progress fill {ratio}'
        classic_checks['progress']=round(ratio,3)

    settings = Gtk.Settings.get_default()
    settings.set_property('gtk-theme-name', family['name'])
    settings.set_property('gtk-font-name', 'DejaVu Sans 10')
    settings.set_property('gtk-enable-animations', False)
    settings.set_property('gtk-cursor-blink', False)
    window = Gtk.OffscreenWindow()
    grid = Gtk.Grid(row_spacing=12, column_spacing=12, margin=18)
    controls = []

    def put(widget, col, row, width=1):
        grid.attach(widget, col, row, width, 1)
        controls.append(widget)
        return widget

    put(Gtk.Button(label='Button'), 0, 0)
    button = put(Gtk.ToggleButton(label='Toggled'), 1, 0)
    button.set_active(True)
    put(Gtk.Entry(text=family['name']+' GTK 3.24'), 2, 0)
    disabled = put(Gtk.Button(label='Disabled'), 3, 0)
    disabled.set_sensitive(False)
    for col, (label, state) in enumerate((('Off', 0), ('On', 1), ('Mixed', 2))):
        check = put(Gtk.CheckButton(label=label), col, 1)
        check.set_active(state == 1)
        check.set_inconsistent(state == 2)
    radio = put(Gtk.RadioButton(label='Radio'), 3, 1)
    radio.set_active(True)
    switch = put(Gtk.Switch(), 0, 2)
    switch.set_active(True)
    scale = put(Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1), 1, 2, 2)
    scale.set_value(40)
    scale.set_size_request(220, -1)
    progress = put(Gtk.ProgressBar(), 3, 2)
    progress.set_fraction(.6)
    combo = put(Gtk.ComboBoxText(), 0, 3)
    combo.append_text('Combo box')
    combo.set_active(0)
    put(Gtk.SpinButton.new_with_range(0, 100, 1), 1, 3)
    notebook = put(Gtk.Notebook(), 2, 3, 2)
    notebook.append_page(Gtk.Label(label='Tab content'), Gtk.Label(label='Tab one'))
    notebook.append_page(Gtk.Label(label='Another page'), Gtk.Label(label='Tab two'))
    label = put(Gtk.Label(label='Selectable label'), 0, 4, 2)
    label.set_selectable(True)
    label.select_region(0, 10)
    text = put(Gtk.TextView(), 2, 4, 2)
    text.get_buffer().set_text('Text view\nSelection and text')
    text.set_size_request(-1, 65)
    vertical = put(Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL, 0, 100, 1), 0, 5)
    vertical.set_value(60)
    vertical.set_size_request(-1, 95)
    spin = put(Gtk.SpinButton.new_with_range(0, 10, 1), 1, 5)
    spin.set_orientation(Gtk.Orientation.VERTICAL)
    level = put(Gtk.LevelBar(), 2, 5)
    level.set_value(.7)
    rows = put(Gtk.ListBox(), 3, 5)
    rows.add(Gtk.Label(label='Selected row', margin=6))
    rows.select_row(rows.get_row_at_index(0))
    # Check and radio indicators in a popover-style menu, including the previously
    # broken hovered indeterminate state. No live window or interactive menu.
    # Real modelbuttons expose the same check/radio CSS nodes used in popovers.
    for i, role in enumerate((Gtk.ButtonRole.CHECK, Gtk.ButtonRole.RADIO)):
        model = put(Gtk.ModelButton(), i, 6)
        model.set_property('text', 'Menu indicator')
        model.set_property('role', role)
        model.set_property('active', True)
        model.set_state_flags(Gtk.StateFlags.INCONSISTENT, False)
    window.add(grid)
    window.show_all()
    assert window.get_style_context().lookup_color('vapor_test_fixture')[0], 'Widget used another theme'
    assert window.get_scale_factor() == 1
    pngs = []
    failures = []
    modes = iter(('normal', 'hover', 'backdrop', 'rtl', 'fine-tune', 'disabled'))

    def next_mode():
        mode = next(modes, None)
        if mode is None:
            Gtk.main_quit()
            return False
        for widget in controls:
            widget.unset_state_flags(Gtk.StateFlags.PRELIGHT | Gtk.StateFlags.BACKDROP)
            widget.set_direction(Gtk.TextDirection.RTL if mode == 'rtl' else Gtk.TextDirection.LTR)
            if mode in ('hover', 'backdrop'):
                widget.set_state_flags(Gtk.StateFlags.PRELIGHT if mode == 'hover' else Gtk.StateFlags.BACKDROP, False)
            if mode == 'disabled':
                widget.set_sensitive(False)
        if mode == 'fine-tune':
            scale.get_style_context().add_class('fine-tune')
        else:
            scale.get_style_context().remove_class('fine-tune')
        window.queue_draw()
        GLib.timeout_add(180, capture, mode)
        return False

    def capture(mode):
        pixbuf = window.get_pixbuf()
        assert pixbuf and pixbuf.get_width() > 100 and pixbuf.get_height() > 100
        file = Path(args.output) / f'{mode}-{os.environ.get("GDK_SCALE", "1")}x.png'
        pixbuf.savev(str(file), 'png', [], [])
        if family['classic']:
            offset=3*pixbuf.get_rowstride()+3*pixbuf.get_n_channels()
            actual=tuple(pixbuf.get_pixels()[offset:offset+3])
            if actual != family['window']:
                failures.append(AssertionError('GTK3-SURFACE: wrong actual window background: '+str(actual)))
                Gtk.main_quit()
                return False
        pngs.append(file.name)
        GLib.idle_add(next_mode)
        return False

    GLib.idle_add(next_mode)
    Gtk.main()
    if failures:raise failures[0]
    report={'gtk': f'{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}',
                      'family':args.family, 'theme_name':settings.get_property('gtk-theme-name'),
                      'display_scale': window.get_scale_factor(),
                      'scaled_indicators': len(indicator_results), 'parsed': len(providers), 'backdrop_selection': selection_rgba,
                      'fine_tune_margin': fine_margin, 'classic_checks':classic_checks,'captures': pngs}
    (Path(args.output)/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', choices=tuple(FAMILY_TOOLS['FAMILIES']))
    parser.add_argument('--theme', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--baseline', action='store_true', help='record old styles without asserting corrected node values')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    supplied_theme = args.theme is not None
    both = args.family is None and args.theme is None and not args.baseline and not args.worker
    args.family = args.family or 'vapor'
    family = FAMILY_TOOLS['get_family'](args.family)
    args.theme = args.theme or ROOT/'usr/share/themes'/family['name']
    if args.baseline and args.family != 'vapor':parser.error('--baseline is for archived Vapor only')
    if args.worker:
        worker(args)
        return
    theme = args.theme.resolve()
    if not args.baseline:
        assert (theme/'gtk-3.24/gtk.css').is_file(), 'Missing GTK 3.24 entry'
        assert (theme/'gtk-3.0/gtk.css').is_file(), 'Missing chooser entry'
        assert not (theme/'gtk-3.18').exists() and not (theme/'gtk-3.20').exists(), 'Obsolete GTK styles remain'
    for css in theme.glob('gtk-3*/*.css'):
        if args.baseline and css.parent.name != 'gtk-3.20':
            continue
        for url in re.findall(r'url\(["\']?([^"\')]+)', css.read_text()):
            assert (css.parent / url).is_file(), f'Missing asset: {css} -> {url}'
    if not args.baseline:
        used = {Path(url).name for css in theme.glob('gtk-3*/*.css')
                for url in re.findall(r'url\(["\']?([^"\')]+)', css.read_text())}
        unused = sorted(f.name for f in (theme/'assets').iterdir() if f.name not in used)
        assert not unused, f'Unreferenced assets: {unused[:5]} ({len(unused)})'
    with tempfile.TemporaryDirectory(prefix='vapor-gtk3-check-') as directory:
        scratch = Path(directory)
        env = os.environ.copy()
        for key, folder in (('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'),
                            ('XDG_CACHE_HOME', 'cache'), ('XDG_DATA_HOME', 'data'),
                            ('XDG_STATE_HOME', 'state'), ('XDG_RUNTIME_DIR', 'runtime')):
            path = scratch / folder
            path.mkdir(mode=0o700)
            env[key] = str(path)
        staged = scratch / 'data/themes'/family['name']
        shutil.copytree(theme, staged)
        for css in staged.glob('gtk-3*/gtk.css'):
            css.write_text('@define-color vapor_test_fixture #11171d;\n' + css.read_text())
        env.update({'XDG_CONFIG_DIRS': str(scratch/'config'), 'XDG_DATA_DIRS': '/usr/share',
                    'GDK_BACKEND': 'broadway', 'BROADWAY_DISPLAY': ':1',
                    'GTK_THEME': family['name'], 'GTK_MODULES': '', 'GTK3_MODULES': '',
                    'NO_AT_BRIDGE': '1', 'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/nonexistent',
                    'GTK_USE_PORTAL': '0', 'GSETTINGS_BACKEND': 'memory',
                    'GDK_DPI_SCALE': '1', 'LC_ALL': 'C.UTF-8'})
        for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'GTK_PATH', 'GTK_DATA_PREFIX',
                    'GTK2_RC_FILES', 'GDK_DEBUG', 'GTK_DEBUG'):
            env.pop(key, None)
        server = subprocess.Popen(['broadwayd', '--unixsocket', str(scratch/'http.socket'), ':1'],
                                  env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if (scratch/'http.socket').exists():
                    break
                if server.poll() is not None:
                    raise RuntimeError(server.communicate())
                time.sleep(.02)
            else:
                raise RuntimeError('Private Broadway server did not become ready')
            output = args.output.resolve() if args.output else scratch/'captures'
            output.mkdir(parents=True, exist_ok=True)
            env['GDK_SCALE'] = '1'
            command = [sys.executable, '-I', str(Path(__file__).resolve()), '--worker',
                       '--family',args.family, '--theme', str(staged), '--output', str(output)]
            if args.baseline:
                command.append('--baseline')
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=25)
            if result.returncode or result.stderr:
                raise RuntimeError(result.stdout + result.stderr)
            print(result.stdout.strip())
        finally:
            server.terminate()
            server.communicate(timeout=5)
    if not args.baseline:
        command = [sys.executable, '-I', str(ROOT/'tools/check-gtk-regressions.py'),
                   '--gtk', '3.0', '--theme', str(theme),'--family',args.family]
        if args.output:
            command += ['--output', str(args.output.resolve()/'behavior')]
        subprocess.run(command, check=True)
        command=[sys.executable,'-I',str(ROOT/'tools/check-gtk3-windows.py'),
                 '--family',args.family,'--theme',str(theme)]
        if args.output:command += ['--output',str(args.output.resolve()/'windows')]
        subprocess.run(command,check=True)
        if args.family=='vgui2' and not supplied_theme:
            subprocess.run([sys.executable,'-I',str(ROOT/'tools/test-vgui2-gtk3.py')],check=True)
    print(f"GTK 3.24 {family['name']} CSS, assets, discovery and rendering: PASS",flush=True)
    if both:
        command=[sys.executable,'-I',str(Path(__file__).resolve()),'--family','vgui2']
        if args.output:command += ['--output',str(args.output.resolve()/'vgui2')]
        subprocess.run(command,check=True)


if __name__ == '__main__':
    main()
