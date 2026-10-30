#!/usr/bin/env python3
"""Test Vapor's optional libadwaita colors using temporary user CSS and real widgets.

Requires GTK 4.24+, libadwaita 1.10+, Python GI/Pillow, gtk4-broadwayd and D-Bus.
Includes light/high-contrast baselines, popup/dialog roots, scale 2, state and
appearance transitions. No user settings or installed theme are modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import warnings

ROOT = Path(__file__).resolve().parent.parent
BROADWAY_WARNING = re.compile(
    r'\([^()\n]+:\d+\): Gdk-WARNING \*\*: [\d:.]+: '
    r'(?:gdk_frame_timings_submitted\(\) called on submitted frame\.|'
    r'Duplicate call to gdk_frame_timings_submitted\(\) with different values\.)')
COLORS = {
    'accent-bg-color':'569fcc', 'accent-fg-color':'1f1f26',
    'window-bg-color':'24272c', 'window-fg-color':'eff0f1',
    'view-bg-color':'151c23', 'view-fg-color':'eff0f1',
    'headerbar-bg-color':'24272c', 'headerbar-fg-color':'eff0f1', 'headerbar-backdrop-color':'24272c',
    'sidebar-bg-color':'151c23', 'sidebar-fg-color':'eff0f1', 'sidebar-backdrop-color':'1a212a',
    'secondary-sidebar-bg-color':'1a212a', 'secondary-sidebar-fg-color':'eff0f1',
    'secondary-sidebar-backdrop-color':'24272c', 'card-bg-color':'2d3136', 'card-fg-color':'eff0f1',
    'dialog-bg-color':'24272c', 'dialog-fg-color':'eff0f1', 'popover-bg-color':'24272c',
    'popover-fg-color':'eff0f1', 'thumbnail-bg-color':'2d3136', 'thumbnail-fg-color':'eff0f1',
    'overview-bg-color':'151c23', 'overview-fg-color':'eff0f1',
    'active-toggle-bg-color':'569fcc', 'active-toggle-fg-color':'1f1f26'}


def contrast(a, b):
    def luminance(rgb):
        values = [v/255/12.92 if v/255 <= .04045 else ((v/255+.055)/1.055)**2.4 for v in rgb]
        return sum(x*y for x,y in zip(values,(.2126,.7152,.0722)))
    low, high = sorted((luminance(a), luminance(b)))
    return (high+.05)/(low+.05)


def worker(args):
    warnings.filterwarnings('ignore', category=DeprecationWarning)
    import gi
    gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
    gi.require_version('Gsk','4.0');gi.require_version('Graphene','1.0')
    from gi.repository import Gtk,Adw,Gio,GLib,Gsk,Graphene
    from PIL import Image
    assert (Gtk.get_major_version(),Gtk.get_minor_version()) >= (4,24), 'GTK 4.24+ required'
    assert (Adw.get_major_version(),Adw.get_minor_version()) >= (1,10), 'libadwaita 1.10+ required'
    Adw.init()
    manager = Adw.StyleManager.get_default()
    manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT if args.light else Adw.ColorScheme.FORCE_DARK)
    settings = Gtk.Settings.get_default()
    settings.set_property('gtk-enable-animations',False)
    settings.set_property('gtk-cursor-blink',False)
    errors = []
    parser = Gtk.CssProvider()
    parser.connect('parsing-error',lambda _p,section,error:errors.append(error.message))
    parser.load_from_path(str(args.profile))
    assert not errors, 'ADW-CSS: '+str(errors)
    # Parsing only; actual profile styling must arrive through the staged user import.
    query = Gtk.CssProvider()
    tokens = (*COLORS, 'accent-color', 'destructive-color', 'error-color', 'warning-color',
              'success-color', 'border-opacity', 'disabled-opacity', 'window-radius')
    query.load_from_string('\n'.join('.vapor-query-'+name+' { color: var(--'+name+'); }'
                                    for name in tokens if name in COLORS or name.endswith('-color')))
    Gtk.StyleContext.add_provider_for_display(Gtk.Widget.get_display(Gtk.Label()),query,Gtk.STYLE_PROVIDER_PRIORITY_USER)
    window = Adw.Window(title='Vapor libadwaita checks')
    window.set_default_size(1050,850)
    toolbar = Adw.ToolbarView()
    header = Adw.HeaderBar();header.set_title_widget(Adw.WindowTitle(title='Vapor',subtitle='libadwaita compatibility'))
    toolbar.add_top_bar(header)
    body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=14,
                   margin_start=20,margin_end=20,margin_top=20,margin_bottom=20)
    groups = Gtk.Box(spacing=20,homogeneous=True)
    group = Adw.PreferencesGroup(title='Appearance')
    action = Adw.ActionRow(title='Native action row',subtitle='Adwaita structure retained')
    switchrow = Adw.SwitchRow(title='Native switch',active=True)
    entryrow = Adw.EntryRow(title='Text',text='Vapor')
    password = Adw.PasswordEntryRow(title='Password',text='example')
    for row in (action,switchrow,entryrow,password):group.add(row)
    groups.append(group)
    group2 = Adw.PreferencesGroup(title='Controls')
    combo = Adw.ComboRow(title='Choice',model=Gtk.StringList.new(['First','Second']))
    expander = Adw.ExpanderRow(title='Expandable',subtitle='Native arrow and spacing')
    expander.add_row(Adw.ActionRow(title='Nested item'))
    spinrow = Adw.SpinRow.new_with_range(0,100,1);spinrow.set_title('Number');spinrow.set_value(50)
    buttonrow = Adw.ButtonRow(title='Suggested action');buttonrow.add_css_class('suggested-action')
    for row in (combo,expander,spinrow,buttonrow):group2.add(row)
    groups.append(group2);body.append(groups)
    buttons = Gtk.Box(spacing=12)
    ordinary = Gtk.Button(label='Ordinary')
    suggested = Gtk.Button(label='Suggested');suggested.add_css_class('suggested-action')
    disabled = Gtk.Button(label='Disabled');disabled.add_css_class('suggested-action');disabled.set_sensitive(False)
    destructive = Gtk.Button(label='Destructive');destructive.add_css_class('destructive-action')
    toggle = Gtk.ToggleButton(label='Checked',active=True)
    for widget in (ordinary,suggested,disabled,destructive,toggle):buttons.append(widget)
    body.append(buttons)
    checks = Gtk.Box(spacing=12)
    checks.append(Gtk.CheckButton(label='Checked',active=True));checks.append(Gtk.Switch(active=True))
    accent = Gtk.Label(label='Readable standalone accent');accent.add_css_class('accent');checks.append(accent)
    body.append(checks)
    rows = Gtk.ListBox();rows.add_css_class('boxed-list')
    row = Gtk.ListBoxRow();selected_label=Gtk.Label(label='Selected content row',xalign=0,
                                                  margin_start=12,margin_top=10,margin_bottom=10)
    row.set_child(selected_label);rows.append(row);rows.select_row(row);body.append(rows)
    text = Gtk.Entry(text='Selected entry text');text.select_region(0,-1);body.append(text)
    banner = Adw.Banner(title='Native banner surface');banner.set_revealed(True);body.append(banner)
    status = Adw.StatusPage(title='Vapor compatibility',description='Color profile; native Adwaita widgets',icon_name='preferences-desktop-theme-symbolic')
    status.add_css_class('compact')
    status.set_vexpand(True);body.append(status)
    queries = {}
    for name in tokens:
        if name not in COLORS and not name.endswith('-color'):continue
        label = Gtk.Label();label.add_css_class('vapor-query-'+name);label.set_visible(False)
        body.append(label);queries[name]=label
    target = body
    toolbar.set_content(body)
    if args.scene == 'sidebar':
        toolbar.set_content(None)
        sidebar = Adw.NavigationPage.new(Adw.StatusPage(title='Primary sidebar'),'Sidebar')
        navigation = Adw.NavigationSplitView()
        navigation.set_sidebar(sidebar);navigation.set_content(Adw.NavigationPage.new(body,'Content'))
        toolbar.set_content(navigation);target=navigation
    overlay = Adw.ToastOverlay();overlay.set_child(toolbar);window.set_content(overlay)
    popup = None
    if args.scene in ('popover','menu'):
        button = Gtk.MenuButton(label='Open popup');header.pack_start(button)
        if args.scene == 'menu':
            model = Gio.Menu();model.append('First action','test.first')
            custom = Gio.MenuItem();custom.set_attribute_value('custom',GLib.Variant('s','controls'));model.append_item(custom)
            actions = Gio.SimpleActionGroup();actions.add_action(Gio.SimpleAction.new('first',None))
            window.insert_action_group('test',actions)
            popup = Gtk.PopoverMenu.new_from_model(model)
            extra = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
            extra.append(Gtk.Label(label='Popup inherits Vapor colors'))
            popup.add_child(extra,'controls')
        else:
            popup = Gtk.Popover();extra=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,
                                               margin_start=16,margin_end=16,margin_top=16,margin_bottom=16)
            extra.append(Gtk.Label(label='Native popover'))
            popup.set_child(extra)
        # Queries inside the actual popup root validate variable inheritance.
        for label in queries.values():body.remove(label);extra.append(label)
        popup_button=Gtk.Button(label='Suggested');popup_button.add_css_class('suggested-action');extra.append(popup_button)
        button.set_popover(popup)
        def open_popup():button.popup();return False
        GLib.timeout_add(150,open_popup)
    dialog = None
    if args.scene == 'dialog':
        toolbar.set_content(Gtk.Label(label='Window beneath dialog'))
        dialog=Adw.Dialog(title='Vapor dialog',content_width=1000,content_height=750)
        dialog.set_child(body)
        GLib.timeout_add(150,lambda: (dialog.present(window),False)[1])
    if args.state=='rtl':window.set_direction(Gtk.TextDirection.RTL)
    window.present()
    loop=GLib.MainLoop();failures=[];phases=[]

    def descendants(widget):
        yield widget
        child=widget.get_first_child()
        while child:
            yield from descendants(child);child=child.get_next_sibling()

    def rgb(widget):
        c=widget.get_color()
        return [max(0,min(255,round(v*255))) for v in (c.red,c.green,c.blue)]

    def apply_test_state():
        if args.state=='backdrop':
            for widget in descendants(window):widget.set_state_flags(Gtk.StateFlags.BACKDROP,False)
        else:
            for widget in descendants(window):widget.unset_state_flags(Gtk.StateFlags.BACKDROP)
        if args.state=='focus':
            suggested.grab_focus();window.set_focus_visible(True)
        return False
    GLib.timeout_add(100,apply_test_state)

    def capture():
        assert window.get_scale_factor()==args.scale,'ADW-SCALE: requested native scale was not applied'
        if args.state=='backdrop':
            assert body.get_state_flags() & Gtk.StateFlags.BACKDROP,'ADW-STATE: backdrop was lost'
        colors={name:rgb(label) for name,label in queries.items()}
        dark=manager.get_dark();hc=manager.get_high_contrast()
        active=not args.baseline and dark and not hc
        for name,expected in COLORS.items():
            if active:
                wanted=[int(expected[i:i+2],16) for i in (0,2,4)]
                assert colors[name]==wanted,f'ADW-COLOR: {name}: {colors[name]} != {wanted}'
        if not active:
            assert colors['accent-bg-color']==[53,132,228], 'ADW-GUARD: non-Vapor appearance was recolored'
            assert colors['window-bg-color']==([34,34,38] if dark else [250,250,251]), 'ADW-GUARD: window changed'
        assert settings.get_property('gtk-theme-name')=='Adwaita-empty','Adwaita providers must remain enabled'
        fg=rgb(suggested.get_child())
        assert fg==([31,31,38] if active else [255,255,255]),f'ADW-FOREGROUND: {fg}'
        assert not disabled.get_sensitive() and suggested.get_sensitive()
        # Capture the actual mapped content, with the real window CSS background.
        snapshot_target = popup.get_child() if popup else target
        if args.scene=='dialog':snapshot_target=body
        if not snapshot_target.get_mapped():
            chain=[];ancestor=snapshot_target
            while ancestor:
                chain.append((type(ancestor).__name__,ancestor.get_visible(),ancestor.get_child_visible(),ancestor.get_mapped(),ancestor.get_width(),ancestor.get_height()))
                ancestor=ancestor.get_parent()
            raise AssertionError(f'ADW-SURFACE: unmapped content: {chain}')
        width,height=snapshot_target.get_width(),snapshot_target.get_height()
        paint=Gtk.WidgetPaintable.new(snapshot_target);snap=Gtk.Snapshot()
        snap.scale(args.scale,args.scale)
        snap.render_background(window.get_style_context(),0,0,width,height)
        paint.snapshot(snap,width,height)
        node=snap.to_node();assert node is not None,'ADW-SNAPSHOT: empty content'
        renderer=Gsk.CairoRenderer.new();renderer.realize(None)
        viewport=Graphene.Rect();viewport.init(0,0,width*args.scale,height*args.scale)
        texture=renderer.render_texture(node,viewport)
        filename=f'{len(phases)}-{args.scene}.png';texture.save_to_png(str(args.output/filename));renderer.unrealize()
        image=Image.open(args.output/filename).convert('RGB')
        assert width>80 and height>50 and len(image.getcolors(image.width*image.height) or [])>20,'ADW-SNAPSHOT: blank image'
        assert image.size==(width*args.scale,height*args.scale)
        bg=None;selected_bg=None;ratios={}
        if popup is None:
            ok,bounds=suggested.compute_bounds(snapshot_target);assert ok
            point=((round(bounds.get_x())+6)*args.scale,round(bounds.get_y()+bounds.get_height()/2)*args.scale)
            bg=list(image.getpixel(point))
            assert bg==([86,159,204] if active else [53,132,228]),f'ADW-PIXEL: suggested fill {bg}'
            ratios['suggested']=round(contrast(fg,bg),2)
            if active:
                assert ratios['suggested']>=4.5,f'ADW-CONTRAST: suggested {ratios}'
            ok,bounds=row.compute_bounds(snapshot_target);assert ok
            selected_bg=list(image.getpixel(((round(bounds.get_x())+6)*args.scale,round(bounds.get_y()+bounds.get_height()/2)*args.scale)))
            ratios['selected-row']=round(contrast(rgb(selected_label),selected_bg),2)
            assert ratios['selected-row']>=4.5,f'ADW-CONTRAST: selected row {ratios}'
        if popup:
            assert popup.get_mapped() and popup.get_native().get_surface() is not None,'ADW-SURFACE: popup missing'
            assert rgb(popup_button.get_child())==([31,31,38] if active else [255,255,255]),'ADW-POPUP: wrong label'
        if dialog:assert dialog.get_mapped(),'ADW-SURFACE: dialog missing'
        if args.state=='focus':
            assert suggested.get_state_flags() & Gtk.StateFlags.FOCUS_VISIBLE,'ADW-FOCUS: visible focus was not established'
            ok,bounds=suggested.compute_bounds(snapshot_target);assert ok
            x=round(bounds.get_x());y=round(bounds.get_y()+bounds.get_height()/2)
            ring=[image.getpixel((px,py)) for px in range(x-6,x) for py in range(y-2,y+3)]
            ratios['focus-ring']=round(max(contrast(pixel,colors['window-bg-color']) for pixel in ring),2)
            assert ratios['focus-ring']>=3,f'ADW-FOCUS: weak ring {ratios}'
        geom={name:[widget.get_width(),widget.get_height()] for name,widget in
              (('ordinary',ordinary),('suggested',suggested),('action-row',action),('switch-row',switchrow),
               ('entry-row',entryrow),('combo-row',combo),('spin-row',spinrow),('button-row',buttonrow))}
        api=manager.get_accent_color_rgba()
        return {'dark':dark,'high_contrast':hc,'active':active,'tokens':colors,'suggested_foreground':fg,
                'suggested_background':bg,'selected_background':selected_bg,'contrast':ratios,'geometry':geom,
                'image':filename,'image_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
                'image_size':list(image.size),'widget_scale':window.get_scale_factor(),
                'popup_mapped':bool(popup and popup.get_mapped()),'dialog_mapped':bool(dialog and dialog.get_mapped()),
                'focus_visible':bool(suggested.get_state_flags() & Gtk.StateFlags.FOCUS_VISIBLE),
                'accent_api':[round(api.red*255),round(api.green*255),round(api.blue*255)],
                'mapped_classes':sorted({type(w).__name__ for w in descendants(window) if w.get_mapped()})}

    def step():
        try:
            phases.append(capture())
            if args.scene=='transition' and len(phases)<3:
                manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT if len(phases)==1 else Adw.ColorScheme.FORCE_DARK)
                GLib.timeout_add(300,step);return False
        except BaseException as error:failures.append(error)
        loop.quit();return False
    GLib.timeout_add(650,step);loop.run()
    if popup:popup.popdown()
    if dialog:dialog.force_close()
    window.destroy()
    if failures:raise failures[0]
    result={'gtk':f'{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}',
            'adwaita':f'{Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}',
            'scene':args.scene,'state':args.state,'scale':args.scale,'baseline':args.baseline,'phases':phases}
    print(json.dumps(result))


def make_environment(scratch,args,overlay):
    env=os.environ.copy()
    for variable,folder in (('HOME','home'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),
                            ('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state'),('XDG_RUNTIME_DIR','runtime')):
        p=scratch/folder;p.mkdir(mode=0o700);env[variable]=str(p)
    config=scratch/'config/gtk-4.0';config.mkdir()
    (config/'settings.ini').write_text('[Settings]\ngtk-theme-name=Vapor\ngtk-font-name=DejaVu Sans 10\n')
    # Exercise the same activation mechanism, preserving a KDE-style import.
    (config/'colors.css').write_text('@define-color theme_bg_color_breeze #24272c;\n')
    (config/'gtk.css').write_text("@import 'colors.css';\n")
    if overlay and not getattr(args,'without_import',False):
        subprocess.run([sys.executable,'-I',str(ROOT/'tools/vapor-libadwaita'),'enable','--json',
                        '--config-home',str(scratch/'config'),'--profile',str(args.profile.resolve())],
                       capture_output=True,text=True,check=True)
    env.update({'XDG_CONFIG_DIRS':str(scratch/'config'),'XDG_DATA_DIRS':'/usr/share',
                'GDK_BACKEND':'broadway','BROADWAY_DISPLAY':':1','GSK_RENDERER':'broadway',
                'GDK_DEBUG':'no-portals','GDK_DISABLE':'gl:vulkan:offload','VK_LOADER_DRIVERS_DISABLE':'*',
                'GTK_A11Y':'none','GTK_MODULES':'','GTK_IM_MODULE':'gtk-im-context-simple','GSETTINGS_BACKEND':'memory',
                'GTK_USE_PORTAL':'0','DBUS_SESSION_BUS_ADDRESS':'unix:path=/nonexistent',
                'GDK_SCALE':str(args.scale),'GDK_DPI_SCALE':'1','LC_ALL':'C.UTF-8',
                'ADW_DISABLE_PORTAL':'1','ADW_DEBUG_COLOR_SCHEME':'prefer-dark',
                'ADW_DEBUG_HIGH_CONTRAST':'1' if args.hc else '0','ADW_DEBUG_ACCENT_COLOR':'blue'})
    for variable in ('GTK_THEME','DISPLAY','WAYLAND_DISPLAY','GTK_PATH','GTK_DATA_PREFIX','GTK_DEBUG',
                     'GSK_DEBUG','LD_PRELOAD','DBUS_STARTER_ADDRESS','DBUS_STARTER_BUS_TYPE','VK_LOADER_DEBUG'):
        env.pop(variable,None)
    bus=scratch/'dbus.conf'
    bus.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(scratch/'runtime')+
                   '</listen><policy context="default"><allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/></policy></busconfig>')
    return env,bus


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,default=ROOT/'libadwaita/vapor.css')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--quick',action='store_true',help='only baseline/profile normal dark fixtures')
    parser.add_argument('--strict',action='store_true',help='also reject known Broadway frame-timing diagnostics')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--scene',default='main',choices=('main','sidebar','dialog','popover','menu','transition'),help=argparse.SUPPRESS)
    parser.add_argument('--state',default='normal',choices=('normal','backdrop','rtl','focus'),help=argparse.SUPPRESS)
    parser.add_argument('--light',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--hc',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--baseline',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--without-import',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--scale',type=int,default=1,choices=(1,2),help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:worker(args);return
    helpers=runpy.run_path(str(ROOT/'tools/check-widget-factory.py'))
    frame_client=runpy.run_path(str(ROOT/'tools/broadway-test-client.py'))['FrameClient']
    with tempfile.TemporaryDirectory(prefix='vapor-adwaita-check-') as folder:
        scratch=Path(folder);output=args.output.resolve() if args.output else scratch/'evidence';output.mkdir(parents=True,exist_ok=True)
        (output/'results.json').unlink(missing_ok=True)
        cases=[('main','normal',False,False,1,True),('main','normal',False,False,1,False)]
        if not args.quick:
            for light,hc in ((True,False),(False,True),(True,True)):
                cases.extend([('main','normal',light,hc,1,baseline) for baseline in (True,False)])
            for scene in ('sidebar','dialog','popover','menu'):
                cases.extend([(scene,'normal',False,False,1,baseline) for baseline in (True,False)])
            cases.extend([('main',state,False,False,1,False) for state in ('backdrop','rtl','focus')])
            cases += [('main','normal',False,False,2,baseline) for baseline in (True,False)]
            cases += [('transition','normal',False,False,1,False)]
        if args.scene != 'main':
            cases=[case for case in cases if case[0]==args.scene]
        if args.state != 'normal':
            cases=[case for case in cases if case[1]==args.state]
        if args.hc:cases=[case for case in cases if case[3] and not case[2]]
        if args.light:cases=[case for case in cases if case[2] and not case[3]]
        assert cases,'No cases selected'
        results=[]
        for index,(scene,state,light,hc,scale,baseline) in enumerate(cases):
            case=f'{index:02}-{scene}-{state}-'+('light' if light else 'dark')+('-hc' if hc else '')+f'-s{scale}-'+('base' if baseline else 'vapor')
            directory=scratch/case;directory.mkdir();case_output=output/case;case_output.mkdir(exist_ok=True)
            options=argparse.Namespace(**vars(args));options.light=light;options.hc=hc;options.scale=scale
            env,bus=make_environment(directory,options,not baseline)
            command=['dbus-run-session','--config-file='+str(bus),'--',sys.executable,'-I',str(Path(__file__).resolve()),
                     '--worker','--profile',str(args.profile.resolve()),'--output',str(case_output),
                     '--scene',scene,'--state',state,'--scale',str(scale)]
            for flag,value in (('--light',light),('--hc',hc),('--baseline',baseline)):
                if value:command.append(flag)
            with helpers['private_display'](directory,env), frame_client(directory/'http.socket',scale) as client:
                code,stdout,stderr=helpers['run_application'](command,env,case_output,'worker')
            lines=[line for line in stderr.splitlines() if line.strip()]
            known=[line for line in lines if BROADWAY_WARNING.fullmatch(line)]
            unexpected=[line for line in lines if not BROADWAY_WARNING.fullmatch(line)]
            if code or unexpected or (args.strict and known):
                raise RuntimeError(f'{case}: exit {code}\n{stdout}\n{stderr}')
            result=json.loads(stdout);result['case']=case
            result['known_broadway_warnings']=known;result['acknowledged_frames']=client.frames
            assert client.frames>0,'Private display did not acknowledge any frames'
            results.append(result)
            print(f'Libadwaita {case}: PASS',flush=True)
        # Baseline/profile pairs preserve widget allocations, upstream semantic
        # colors, and exact light/high-contrast images in this deterministic fixture.
        for baseline in results:
            if not baseline['baseline']:continue
            matches=[r for r in results if not r['baseline'] and
                     (r['scene'],r['state'],r['scale'],r['phases'][0]['dark'],r['phases'][0]['high_contrast'])==
                     (baseline['scene'],baseline['state'],baseline['scale'],baseline['phases'][0]['dark'],baseline['phases'][0]['high_contrast'])]
            assert matches,'Missing corresponding overlay case'
            base=baseline['phases'][0];overlay=matches[0]['phases'][0]
            assert base['geometry']==overlay['geometry'],'ADW-GEOMETRY: profile changed widget allocations'
            for name in ('destructive-color','success-color','warning-color','error-color'):
                assert base['tokens'][name]==overlay['tokens'][name],f'ADW-SEMANTIC: {name}'
            if not overlay['active']:
                assert base['image_sha256']==overlay['image_sha256'],'ADW-GUARD: fallback rendering changed'
        report={'profile_sha256':hashlib.sha256(args.profile.read_bytes()).hexdigest(),
                'backend':'Broadway','native_renderer':'Broadway','snapshot_renderer':'Cairo','cases':results,
                'limits':['synthetic focus/backdrop; no desktop keyboard input','fractional/live GPU untested','accent API remains system color']}
        (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
        print(f'Libadwaita color/geometry/appearance tests: PASS ({len(results)} cases)',flush=True)
        if args.output:print('Retained evidence:',output)


if __name__=='__main__':main()
