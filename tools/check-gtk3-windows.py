#!/usr/bin/env python3
"""Render mapped GTK 3 windows, popups and dialogs on a private display.

--meld also checks the installed Meld startup view without opening any files.
All HOME/XDG state and the service-free session bus are temporary. No desktop
input is sent. Snapshots use the mapped widgets' native GTK/Cairo drawing.
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent
FAMILY_TOOLS=runpy.run_path(str(ROOT/'tools/theme-families.py'))
FrameClient=runpy.run_path(str(ROOT/'tools/broadway3-test-client.py'))['FrameClient']


def worker(args):
    import warnings
    warnings.filterwarnings('ignore',category=DeprecationWarning)
    import gi
    gi.require_version('Gtk','3.0')
    from gi.repository import Gtk,Gdk,GLib,Gio
    import cairo
    from PIL import Image
    family=FAMILY_TOOLS['get_family'](args.family)
    Gtk.init([])
    settings=Gtk.Settings.get_default()
    settings.set_property('gtk-theme-name',family['name'])
    settings.set_property('gtk-enable-animations',False)
    settings.set_property('gtk-cursor-blink',False)
    settings.set_property('gtk-font-name','DejaVu Sans 10')
    failures=[];reports=[];loop=GLib.MainLoop()
    verify_states=None

    def capture(widget,name):
        assert widget.get_mapped(),name+' did not map'
        width,height=widget.get_allocated_width(),widget.get_allocated_height()
        assert width>20 and height>20,(name,width,height)
        surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,width,height)
        widget.draw(cairo.Context(surface))
        path=args.output/(name+'.png');surface.write_to_png(str(path))
        with Image.open(path) as source:image=source.convert('RGBA')
        colors=image.getcolors(width*height)
        assert colors and len(colors)>15,name+' rendered blank'
        count=sum(count for count,pixel in colors if tuple(pixel[:3])==family['window'] and pixel[3]==255)
        assert count>width*height*.02,(name,'actual window color missing',count)
        found,color=widget.get_style_context().lookup_color('theme_selected_bg_color')
        assert found and tuple(round(v*255) for v in (color.red,color.green,color.blue))==family['selection']
        assert settings.get_property('gtk-theme-name')==family['name']
        reports.append({'scene':name,'size':[width,height],'window_pixels':count,'mapped':True,
                        'theme':family['name'],'image':path.name})
        if verify_states is not None:
            reports[-1]['state_checks']=verify_states(widget,image,args.output)

    def finish():
        try:
            if args.scene=='meld':
                windows=[w for w in Gtk.Window.list_toplevels() if w.get_visible()]
                assert windows,'Meld has no visible window'
                capture(max(windows,key=lambda w:w.get_allocated_width()),'meld')
            else:
                capture(target,args.scene)
        except BaseException as error:failures.append(error)
        if args.scene=='meld':
            app=Gio.Application.get_default()
            if app:app.quit()
        else:loop.quit()
        return False

    if args.scene=='meld':
        assert shutil.which('meld'),'Install meld for --meld'
        GLib.timeout_add(1200,finish)
        sys.argv=[shutil.which('meld')]
        try:runpy.run_path(sys.argv[0],run_name='__main__')
        except SystemExit as error:
            if error.code not in (0,None):raise
    else:
        window=Gtk.Window(title=family['name']+' GTK 3.24')
        window.set_default_size(790,510)
        header=Gtk.HeaderBar(title='Classic GTK 3 controls',show_close_button=True)
        window.set_titlebar(header)
        body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin=18)
        window.add(body)
        title=Gtk.Label(label='Olive surfaces, raised edges, gold selections',xalign=0)
        body.pack_start(title,False,False,0)
        buttons=Gtk.Box(spacing=8)
        for name,style in (('Ordinary',''),('Suggested','suggested-action'),('Destructive','destructive-action')):
            button=Gtk.Button(label=name)
            if style:button.get_style_context().add_class(style)
            buttons.pack_start(button,False,False,0)
        link=Gtk.LinkButton(uri='https://example.invalid',label='Link (not activated)')
        buttons.pack_start(link,False,False,0);body.pack_start(buttons,False,False,0)
        panes=Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        rows=Gtk.ListBox();rows.get_style_context().add_class('sidebar')
        for name in ('Selected item','Another item','Sidebar item'):
            rows.add(Gtk.Label(label=name,margin=10,xalign=0))
        rows.select_row(rows.get_row_at_index(0));panes.add1(rows)
        fields=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_start=12)
        fields.pack_start(Gtk.Entry(text='Editable content'),False,False,0)
        fields.pack_start(Gtk.CheckButton(label='Classic checkbox',active=True),False,False,0)
        fields.pack_start(Gtk.CheckButton(label='Mixed checkbox',inconsistent=True),False,False,0)
        fields.pack_start(Gtk.RadioButton(label='Classic radio',active=True),False,False,0)
        fields.pack_start(Gtk.SpinButton.new_with_range(0,100,1),False,False,0)
        fields.pack_start(Gtk.Calendar(),True,True,0);panes.add2(fields);panes.set_position(210)
        body.pack_start(panes,True,True,0)
        body.pack_start(Gtk.ProgressBar(fraction=.65),False,False,0)
        anchor=Gtk.MenuButton(label='Menu / popover');header.pack_end(anchor)
        if args.scene in ('states','notebooks'):
            for child in body.get_children():body.remove(child)
            if args.scene=='states':
                state_tools=runpy.run_path(str(ROOT/'tools/gtk3-state-checks.py'))
                apply_states,verify_states=state_tools['build'](Gtk,body)
                GLib.timeout_add(200,apply_states)
            else:
                notebook_tools=runpy.run_path(str(ROOT/'tools/gtk3-notebook-checks.py'))
                verify_states=notebook_tools['build'](Gtk,body)
        target=window;window.show_all()
        if args.scene=='dialog':
            target=Gtk.Dialog(title='Classic dialog',transient_for=window)
            target.add_buttons('Cancel',Gtk.ResponseType.CANCEL,'Accept',Gtk.ResponseType.ACCEPT)
            target.get_content_area().add(Gtk.Label(label='Dialog content; no action is activated.',margin=24))
            target.show_all()
        elif args.scene=='filechooser':
            target=Gtk.FileChooserDialog(title='Test chooser (no file opened)',transient_for=window,
                                         action=Gtk.FileChooserAction.OPEN)
            target.add_buttons('Cancel',Gtk.ResponseType.CANCEL,'Open',Gtk.ResponseType.ACCEPT)
            target.set_current_folder(os.environ['HOME']);target.show_all()
        elif args.scene=='popover':
            target=Gtk.Popover.new(anchor)
            contents=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,margin=12)
            contents.add(Gtk.Label(label='Native popover'))
            contents.add(Gtk.ModelButton(text='Checked menu item',role=Gtk.ButtonRole.CHECK,active=True))
            contents.add(Gtk.ModelButton(text='Another menu item'))
            target.add(contents);anchor.set_popover(target);target.show_all();anchor.set_active(True)
        elif args.scene=='menu':
            target=Gtk.Menu()
            for item in (Gtk.MenuItem(label='First item'),Gtk.CheckMenuItem(label='Checked item',active=True),
                         Gtk.SeparatorMenuItem(),Gtk.MenuItem(label='Last item')):target.append(item)
            target.show_all()
            event=Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
            event.window=window.get_window();event.button=1;event.time=Gdk.CURRENT_TIME
            event.set_device(Gdk.Display.get_default().get_default_seat().get_pointer())
            # A real click happens after the header has an allocation. Opening
            # immediately after show_all anchors the menu to a 1x1 widget.
            def open_menu():
                target.popup_at_widget(anchor,Gdk.Gravity.SOUTH_WEST,Gdk.Gravity.NORTH_WEST,event)
                return False
            GLib.timeout_add(150,open_menu)
        GLib.timeout_add(700,finish);loop.run()
        target.destroy()
        if target is not window:window.destroy()
    if failures:raise failures[0]
    assert reports,'Application exited before capture'
    print(json.dumps(reports[0]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family',choices=tuple(FAMILY_TOOLS['FAMILIES']),default='vgui2')
    parser.add_argument('--theme',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--meld',action='store_true')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--scene',choices=('window','dialog','popover','menu','filechooser','states','notebooks','meld'),help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:worker(args);return
    family=FAMILY_TOOLS['get_family'](args.family)
    theme=(args.theme or ROOT/'usr/share/themes'/family['name']).resolve()
    with tempfile.TemporaryDirectory(prefix='gtk3-window-check-') as name:
        scratch=Path(name);env=os.environ.copy()
        for key,directory in (('HOME','home'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),
                              ('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state'),('XDG_RUNTIME_DIR','runtime')):
            path=scratch/directory;path.mkdir(mode=0o700);env[key]=str(path)
        shutil.copytree(theme,scratch/'data/themes'/family['name'])
        env.update({'XDG_CONFIG_DIRS':str(scratch/'config'),'XDG_DATA_DIRS':'/usr/share',
                    'GTK_THEME':family['name'],'GDK_BACKEND':'broadway','BROADWAY_DISPLAY':':1',
                    'GTK_USE_PORTAL':'0','GTK_MODULES':'','GTK3_MODULES':'','NO_AT_BRIDGE':'1',
                    'GSETTINGS_BACKEND':'memory','GIO_USE_VFS':'local','LC_ALL':'C.UTF-8','GDK_SCALE':'1','GDK_DPI_SCALE':'1'})
        for key in ('DISPLAY','WAYLAND_DISPLAY','GTK_PATH','GTK_DATA_PREFIX','GTK_DEBUG','GDK_DEBUG','DBUS_SESSION_BUS_ADDRESS'):
            env.pop(key,None)
        bus=scratch/'bus.conf'
        bus.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(scratch)+
                       '</listen><auth>EXTERNAL</auth><policy context="default"><allow own="*"/>'+
                       '<allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>')
        server=subprocess.Popen(['broadwayd','-u',str(scratch/'http.socket'),':1'],env=env,
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if (scratch/'http.socket').exists():break
                if server.poll() is not None:raise RuntimeError(server.communicate())
                time.sleep(.02)
            else:raise RuntimeError('Private GTK 3 display did not start')
            output=args.output.resolve() if args.output else scratch/'evidence';output.mkdir(parents=True,exist_ok=True)
            reports=[]
            scenes=(args.scene,) if args.scene else ('window','dialog','popover','menu','filechooser')+(('states','notebooks') if family['classic'] else ())+(('meld',) if args.meld else ())
            for scene in scenes:
                command=['dbus-run-session','--config-file='+str(bus),'--',sys.executable,'-I',str(Path(__file__).resolve()),
                         '--worker','--family',args.family,'--scene',scene,'--output',str(output)]
                with FrameClient(scratch/'http.socket') as client:
                    result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=20)
                assert client.frames>0,'Private GTK 3 display did not process image buffers'
                (output/(scene+'.stdout')).write_text(result.stdout)
                (output/(scene+'.stderr')).write_text(result.stderr)
                if result.returncode or result.stderr:raise RuntimeError(scene+': '+result.stdout+result.stderr)
                report=json.loads(result.stdout.splitlines()[-1]);report['display_buffers']=client.frames;reports.append(report)
                print(f"GTK 3 {family['name']} {scene}: PASS",flush=True)
            (output/'results.json').write_text(json.dumps(reports,indent=2)+'\n')
        finally:server.terminate();server.communicate(timeout=5)


if __name__=='__main__':main()
