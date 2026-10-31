#!/usr/bin/env python3
"""Parse and render Vapor and VGUI2 Classic GTK 4 without touching the desktop.

Requires gtk4 >= 4.24 (gtk4-broadwayd and development/pkg-config files),
gtk4-demos, pkgconf, a C compiler, dbus-run-session, python-gobject,
python-pillow, libadwaita >= 1.10 (Adw GI data) and fonts. Includes Widget Factory,
libadwaita fixtures, coexistence, activation and negative-control tests.
Creates a private Unix-socket display and temporary HOME/XDG settings. Captures
can be retained with --output DIR. Tested on GTK 4.24.1 with the Cairo renderer.
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
    family=FAMILY_TOOLS['get_family'](args.family)
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Gsk', '4.0')
    gi.require_version('Graphene', '1.0')
    from gi.repository import Gtk, GLib, Gio, Gsk, Graphene
    from PIL import Image
    assert Gtk.get_major_version() == 4 and Gtk.get_minor_version() >= 24
    theme = Path(args.theme)
    errors = []
    providers = []
    for path in sorted((theme/'gtk-4.0').glob('*.css')):
        provider = Gtk.CssProvider()
        provider.connect('parsing-error', lambda _p, s, e: errors.append(
            f'{s.get_start_location().lines+1}: {e.message}'))
        provider.load_from_path(str(path))
        providers.append(provider)
    assert not errors, '\n'.join(errors)
    Gtk.init()
    renderer = Gsk.CairoRenderer.new()
    renderer.realize(None)
    settings = Gtk.Settings.get_default()
    settings.set_property('gtk-interface-color-scheme', Gtk.InterfaceColorScheme.DARK if args.dark else Gtk.InterfaceColorScheme.LIGHT)
    settings.set_property('gtk-enable-animations', False)
    settings.set_property('gtk-cursor-blink', False)
    assert settings.get_property('gtk-theme-name') == family['name']
    selection_fg = family['selection_foreground']
    selection_bg = family['selection']

    def rgb(widget):
        color = widget.get_color()
        return tuple(round(v*255) for v in (color.red, color.green, color.blue))

    window = Gtk.Window(title=family['name']+' GTK 4 port test')
    window.set_default_size(820, 620)
    header = Gtk.HeaderBar()
    header.set_title_widget(Gtk.Label(label=family['name']+' GTK 4 — development preview'))
    window.set_titlebar(header)
    grid = Gtk.Grid(row_spacing=12, column_spacing=12,
                    margin_start=20, margin_end=20, margin_top=20, margin_bottom=20)
    grid.set_column_homogeneous(True)
    grid.add_css_class('vapor-gtk4-test-surface')
    controls = []

    def put(widget, col, row, width=1):
        grid.attach(widget, col, row, width, 1)
        controls.append(widget)
        return widget

    normal = put(Gtk.Button(label='Button'), 0, 0)
    toggle = put(Gtk.ToggleButton(label='Toggled', active=True), 1, 0)
    entry = put(Gtk.Entry(text='Entry text'), 2, 0, 2)
    entry.select_region(0, 5)
    checks = []
    for col, (label, active, mixed) in enumerate((('Off', False, False), ('On', True, False), ('Mixed', False, True))):
        checks.append(put(Gtk.CheckButton(label=label, active=active, inconsistent=mixed), col, 1))
    radio1 = put(Gtk.CheckButton(label='Radio A'), 0, 2)
    radio2 = put(Gtk.CheckButton(label='Radio B', group=radio1, active=True), 1, 2)
    switch = put(Gtk.Switch(active=True, halign=Gtk.Align.START), 2, 2)
    scale = put(Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1), 0, 3, 2)
    scale.set_value(40)
    scale.set_size_request(240, -1)
    progress = put(Gtk.ProgressBar(fraction=.6), 2, 3, 2)
    dropdown = put(Gtk.DropDown.new_from_strings(['Vapor dropdown', 'Second choice']), 0, 4)
    spin = put(Gtk.SpinButton.new_with_range(0, 100, 1), 1, 4)
    notebook = put(Gtk.Notebook(), 2, 4, 2)
    notebook.append_page(Gtk.Label(label='Tab content'), Gtk.Label(label='One'))
    notebook.append_page(Gtk.Label(label='Second page'), Gtk.Label(label='Two'))
    selectable = put(Gtk.Label(label='Selected text', selectable=True), 0, 5, 2)
    selectable.select_region(0, 8)
    text = put(Gtk.TextView(), 2, 5, 2)
    text.get_buffer().set_text('GTK 4 text view\nVapor selection palette')
    text.set_size_request(-1, 65)

    factory = Gtk.SignalListItemFactory()
    labels = []

    def setup(_factory, item):
        label = Gtk.Label(xalign=0)
        labels.append(item)
        item.set_child(label)

    def bind(_factory, item):
        label = item.get_child()
        label.set_label(item.get_item().get_string())
        if args.state == 'backdrop':
            label.set_state_flags(Gtk.StateFlags.BACKDROP, False)
            parent = label.get_parent()
            while parent and parent.get_css_name() not in ('listview','columnview'):
                parent.set_state_flags(Gtk.StateFlags.BACKDROP, False)
                parent = parent.get_parent()

    factory.connect('setup', setup)
    factory.connect('bind', bind)
    model = Gtk.SingleSelection.new(Gtk.StringList.new(['Selected list row', 'Another row']))
    view = Gtk.ListView(model=model, factory=factory)
    scroll = put(Gtk.ScrolledWindow(child=view, min_content_height=85), 0, 6, 2)
    columns_model = Gtk.SingleSelection.new(Gtk.StringList.new(['Selected table row', 'Another table row']))
    columns = Gtk.ColumnView(model=columns_model)
    table_labels = []
    column_factory = Gtk.SignalListItemFactory()
    def column_setup(_f, item):
        label = Gtk.Label(xalign=0)
        table_labels.append(item)
        item.set_child(label)
    column_factory.connect('setup', column_setup)
    column_factory.connect('bind', bind)
    columns.append_column(Gtk.ColumnViewColumn(title='Column header', factory=column_factory))
    put(Gtk.ScrolledWindow(child=columns, min_content_height=85), 2, 6, 2)

    menu = Gio.Menu()
    menu.append('Menu action', 'test.action')
    menu.append('Checked option', 'test.checked')
    actions = Gio.SimpleActionGroup()
    actions.add_action(Gio.SimpleAction.new('action', None))
    actions.add_action(Gio.SimpleAction.new_stateful('checked', None, GLib.Variant.new_boolean(True)))
    window.insert_action_group('test', actions)
    popover = Gtk.PopoverMenu.new_from_model(menu)
    menu_button = put(Gtk.MenuButton(label='Popover menu', popover=popover), 0, 7)
    marker = put(Gtk.Label(label=''), 3, 7)
    marker.add_css_class('vapor-gtk4-test-marker')
    window.set_child(grid)
    loop = GLib.MainLoop()
    failure = []
    captures = []
    modes = iter((args.state,))

    def descendants(widget):
        yield widget
        child = widget.get_first_child()
        while child:
            yield from descendants(child)
            child = child.get_next_sibling()

    def snapshot(widget, filename):
        paintable = Gtk.WidgetPaintable.new(widget)
        snap = Gtk.Snapshot()
        paintable.snapshot(snap, widget.get_width(), widget.get_height())
        node = snap.to_node()
        assert node is not None, (filename, widget.get_width(), widget.get_height(), widget.get_mapped())
        viewport = Graphene.Rect()
        viewport.init(0, 0, widget.get_width(), widget.get_height())
        texture = renderer.render_texture(node, viewport)
        assert texture.save_to_png(str(Path(args.output)/filename))
        captures.append(filename)
        return Image.open(Path(args.output)/filename).convert('RGBA')

    def next_mode():
        try:
            mode = next(modes, None)
            if mode is None:
                loop.quit()
                return False
            popover.popdown()
            window.set_focus(None)
            for widget in descendants(grid):
                widget.unset_state_flags(Gtk.StateFlags.PRELIGHT | Gtk.StateFlags.BACKDROP | Gtk.StateFlags.FOCUS_VISIBLE | Gtk.StateFlags.FOCUSED)
                widget.set_direction(Gtk.TextDirection.RTL if mode == 'rtl' else Gtk.TextDirection.LTR)
                if mode in ('hover', 'backdrop'):
                    widget.set_state_flags(Gtk.StateFlags.PRELIGHT if mode == 'hover' else Gtk.StateFlags.BACKDROP, False)
            if mode == 'disabled':
                for control in controls:
                    control.set_sensitive(False)
            GLib.timeout_add(250, capture, mode)
        except BaseException as error:
            failure.append(error)
            loop.quit()
        return False

    def capture(mode):
        try:
            assert window.get_scale_factor() == 1, 'This fixture only claims normal-scale window coverage'
            if mode == 'normal':
                assert rgb(marker) == (17, 23, 29), 'Widgets did not load the staged '+family['name']+' theme'
            assert checks[0].get_first_child().get_css_name() == 'check'
            assert radio2.get_first_child().get_css_name() == 'radio'
            assert spin.get_first_child().get_css_name() == 'text'
            assert entry.get_first_child().get_css_name() == 'text'
            if mode in ('normal', 'backdrop', 'rtl'):
                assert labels and table_labels
                list_label = next(item.get_child() for item in labels if item.get_selected())
                table_label = next(item.get_child() for item in table_labels if item.get_selected())
                def path_for(label):
                    result=[]
                    while label:
                        result.append([label.get_css_name(), label.get_css_classes(), int(label.get_state_flags()), rgb(label)])
                        label=label.get_parent()
                    return result
                (Path(args.output)/'node-diagnostic.json').write_text(json.dumps({'list':path_for(list_label),'table':path_for(table_label)},indent=2))
                assert rgb(list_label) == selection_fg, (mode, 'list', rgb(list_label))
                assert rgb(table_label) == selection_fg, (mode, 'table', rgb(table_label))
                assert rgb(normal) == family['foreground'], (mode, rgb(normal))
            suffix = 'dark' if args.dark else 'normal'
            image = snapshot(grid, f'{mode}-{suffix}.png')
            if mode == 'normal':
                assert image.width > 400 and image.height > 300
                assert any(p[:3] == selection_bg for p in image.get_flattened_data()), 'GTK4-PALETTE: no exact selection background'
            loop.quit()
        except BaseException as error:
            failure.append(error)
            loop.quit()
        return False

    next_mode()
    window.present()
    loop.run()
    window.destroy()
    renderer.unrealize()
    if failure:
        raise failure[0]
    print(json.dumps({'gtk':f'{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}',
                      'family':args.family,'theme_name':family['name'],
                      'variant':'dark' if args.dark else 'normal', 'state':args.state, 'parse_errors':len(errors),
                      'captures':captures, 'selection':selection_bg, 'foreground':selection_fg,
                      'display_scale':1}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--family',choices=tuple(FAMILY_TOOLS['FAMILIES']))
    parser.add_argument('--theme', type=Path)
    parser.add_argument('--libadwaita-profile', type=Path, default=ROOT/'libadwaita/vapor.css')
    parser.add_argument('--overlay', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--state', default='normal', choices=('normal','hover','backdrop','rtl','disabled'), help=argparse.SUPPRESS)
    parser.add_argument('--dark', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    supplied_theme=args.theme is not None
    both=args.family is None and args.theme is None and not args.worker and not args.overlay
    args.family=args.family or 'vapor'
    family=FAMILY_TOOLS['get_family'](args.family)
    args.theme=args.theme or ROOT/'usr/share/themes'/family['name']
    if args.worker:
        worker(args)
        return
    theme = args.theme.resolve()
    for path in (theme/'gtk-4.0').glob('*.css'):
        for url in re.findall(r'url\(["\']?([^"\')]+)', path.read_text()):
            assert (path.parent/url).is_file(), (path, url)
    assert (theme/'gtk-4.0/gtk.css').is_file() and (theme/'gtk-4.0/gtk-dark.css').is_file()
    with tempfile.TemporaryDirectory(prefix='vapor-gtk4-check-') as name:
        scratch = Path(name)
        env = os.environ.copy()
        for variable, folder in (('HOME','home'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),
                                 ('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state'),('XDG_RUNTIME_DIR','runtime')):
            path = scratch/folder
            path.mkdir(mode=0o700)
            env[variable] = str(path)
        config = scratch/'config/gtk-4.0'
        config.mkdir()
        (config/'settings.ini').write_text('[Settings]\ngtk-theme-name='+family['name']+'\ngtk-font-name=DejaVu Sans 10\n')
        if args.overlay:
            subprocess.run([sys.executable,'-I',str(ROOT/'tools/vapor-libadwaita'),'enable',
                            '--config-home',str(scratch/'config'),'--profile',str(args.overlay.resolve()),'--json'],
                           capture_output=True,text=True,check=True)
        staged = scratch/'data/themes'/family['name']
        shutil.copytree(theme, staged)
        css = staged/'gtk-4.0/gtk.css'
        css.write_text(css.read_text()+'\n.vapor-gtk4-test-marker {color: #11171d;}\n.vapor-gtk4-test-surface {background-color: @theme_bg_color;}\n')
        env.update({'XDG_CONFIG_DIRS':str(scratch/'config'),'XDG_DATA_DIRS':'/usr/share',
                    'GDK_BACKEND':'broadway','BROADWAY_DISPLAY':':1','GSK_RENDERER':'cairo',
                    'GTK_A11Y':'none','GTK_MODULES':'','GSETTINGS_BACKEND':'memory',
                    'DBUS_SESSION_BUS_ADDRESS':'unix:path=/nonexistent','LC_ALL':'C.UTF-8',
                    'GDK_SCALE':'1','GDK_DPI_SCALE':'1'})
        for variable in ('GTK_THEME','GTK_PATH','GTK_DATA_PREFIX','DISPLAY','WAYLAND_DISPLAY',
                         'GTK_DEBUG','GSK_DEBUG','GDK_DEBUG'):
            env.pop(variable, None)
        server = subprocess.Popen(['gtk4-broadwayd','--unixsocket',str(scratch/'http.socket'),':1'],
                                  env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if (scratch/'http.socket').exists():
                    break
                if server.poll() is not None:
                    raise RuntimeError(server.communicate())
                time.sleep(.02)
            else:
                raise RuntimeError('Private GTK 4 display did not start')
            output = args.output.resolve() if args.output else scratch/'captures'
            output.mkdir(parents=True,exist_ok=True)
            reports=[]
            for dark in (False, True):
                for state in ('normal', 'hover', 'backdrop', 'rtl', 'disabled'):
                    command = [sys.executable,'-I',str(Path(__file__).resolve()),'--worker',
                               '--family',args.family,'--theme',str(staged),'--output',str(output),'--state',state]
                    if dark:
                        command.append('--dark')
                    result = subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
                    if result.returncode or result.stderr:
                        raise RuntimeError(result.stdout+result.stderr)
                    print(result.stdout.strip(),flush=True)
                    reports.append(json.loads(result.stdout))
            (output/'results.json').write_text(json.dumps(reports,indent=2)+'\n')
        finally:
            server.terminate()
            server.communicate(timeout=5)
    command = [sys.executable, '-I', str(ROOT/'tools/check-gtk-regressions.py'),
               '--gtk', '4.0', '--theme', str(theme),'--family',args.family]
    if args.output:
        command += ['--output', str(args.output.resolve()/'behavior')]
    if args.overlay:
        command += ['--user-css', str(args.overlay.resolve())]
    subprocess.run(command, check=True)
    command = [sys.executable, '-I', str(ROOT/'tools/check-widget-factory.py'),
               '--theme', str(theme),'--family',args.family]
    if args.output:
        command += ['--output', str(args.output.resolve()/'widget-factory')]
    if args.overlay:
        command += ['--user-css', str(args.overlay.resolve())]
    subprocess.run(command, check=True)
    if args.overlay:
        print('Plain GTK 4 widgets, behavior and Widget Factory with libadwaita overlay: PASS',flush=True)
        return
    if family['classic']:
        command=[sys.executable,'-I',str(ROOT/'tools/check-vgui2-gtk4.py'),'--theme',str(theme)]
        if args.output:command += ['--output',str(args.output.resolve()/'classic')]
        subprocess.run(command,check=True)
        if not supplied_theme:
            subprocess.run([sys.executable,'-I',str(ROOT/'tools/test-vgui2-gtk4.py')],check=True)
        print('GTK 4 VGUI2 Classic native, behavior, Widget Factory and state checks: PASS',flush=True)
        return
    command=[sys.executable,'-I',str(Path(__file__).resolve()),'--family',args.family,'--theme',str(theme),
             '--overlay',str(args.libadwaita_profile.resolve())]
    if args.output:command += ['--output',str(args.output.resolve()/'coexistence')]
    subprocess.run(command,check=True)
    command=[sys.executable,'-I',str(ROOT/'tools/check-libadwaita.py'),
             '--profile',str(args.libadwaita_profile.resolve())]
    if args.output:command += ['--output',str(args.output.resolve()/'libadwaita')]
    subprocess.run(command,check=True)
    subprocess.run([sys.executable,'-I',str(ROOT/'tools/test-libadwaita-activation.py')],check=True)
    subprocess.run([sys.executable,'-I',str(ROOT/'tools/test-libadwaita-regressions.py')],check=True)
    subprocess.run([sys.executable,'-I',str(ROOT/'tools/test-package-staging.py')],check=True)
    print('GTK 4 native/Widget Factory, libadwaita, coexistence, activation and negative controls: PASS',flush=True)
    if both:
        command=[sys.executable,'-I',str(Path(__file__).resolve()),'--family','vgui2']
        if args.output:command += ['--output',str(args.output.resolve()/'vgui2')]
        subprocess.run(command,check=True)


if __name__ == '__main__':
    main()
