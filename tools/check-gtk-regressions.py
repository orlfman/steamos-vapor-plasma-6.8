#!/usr/bin/env python3
"""Behavior regressions for inactive toggle labels and spin-button backgrounds.

Called by check-gtk3.py/check-gtk4.py. Uses private Unix-socket displays and
scratch themes/settings; never changes the installed theme. Each state runs
in its own toolkit process. --output retains the native matrix screenshots.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import runpy
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parent.parent
FAMILY_TOOLS=runpy.run_path(str(ROOT/'tools/theme-families.py'))


def contrast(a, b):
    def luminance(rgb):
        v=[c/255/12.92 if c/255<=.04045 else ((c/255+.055)/1.055)**2.4 for c in rgb]
        return sum(x*y for x,y in zip(v,(.2126,.7152,.0722)))
    low,high=sorted((luminance(a),luminance(b)))
    return (high+.05)/(low+.05)


def worker(args):
    family=FAMILY_TOOLS['get_family'](args.family)
    import gi
    gi.require_version('Gtk', args.gtk)
    if args.gtk == '4.0':
        gi.require_version('Gsk','4.0');gi.require_version('Graphene','1.0')
        from gi.repository import Gsk, Graphene
    else:
        import cairo
    from gi.repository import Gtk, GLib
    from PIL import Image
    Gtk.init([]) if args.gtk == '3.0' else Gtk.init()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    if args.gtk=='4.0' and args.user_css:
        Gtk.Settings.get_default().set_property('gtk-interface-color-scheme',Gtk.InterfaceColorScheme.DARK)
    window=Gtk.OffscreenWindow() if args.gtk=='3.0' else Gtk.Window()
    grid=Gtk.Grid(row_spacing=12,column_spacing=12)
    grid.set_column_homogeneous(True)
    spins=[]
    def children(widget):
        if args.gtk=='3.0':
            return widget.get_children() if isinstance(widget,Gtk.Container) else []
        result=[];child=widget.get_first_child()
        while child:result.append(child);child=child.get_next_sibling()
        return result
    def descendants(widget):
        yield widget
        for child in children(widget):yield from descendants(child)
    for col,(name,value,sensitive) in enumerate((('min',0,True),('mid',50,True),('max',100,True),('disabled',50,False))):
        grid.attach(Gtk.Label(label=name),col,0,1,1)
        for row,orientation in ((1,Gtk.Orientation.HORIZONTAL),(2,Gtk.Orientation.VERTICAL)):
            spin=Gtk.SpinButton.new_with_range(0,100,1)
            spin.set_value(value);spin.set_orientation(orientation);spin.set_sensitive(sensitive)
            spin.set_size_request(130,105 if row==2 else -1)
            grid.attach(spin,col,row,1,1)
            spins.append((spin,'horizontal' if row==1 else 'vertical',name,value,sensitive))
    toggle=Gtk.ToggleButton(label='Toggled');toggle.set_active(True)
    ordinary=Gtk.Button(label='Ordinary')
    disabled=Gtk.ToggleButton(label='Disabled checked');disabled.set_active(True);disabled.set_sensitive(False)
    grid.attach(toggle,0,3,2,1);grid.attach(ordinary,2,3,1,1);grid.attach(disabled,3,3,1,1)
    pressed=Gtk.Button(label='Pressed');pressed.set_state_flags(Gtk.StateFlags.ACTIVE,False)
    grid.attach(pressed,0,4,2,1)
    if args.state=='backdrop':
        for widget in descendants(grid):widget.set_state_flags(Gtk.StateFlags.BACKDROP,False)
    if args.gtk=='3.0':window.add(grid);window.show_all()
    else:window.set_child(grid);window.present()
    loop=GLib.MainLoop();failures=[];result={}
    def color(widget):
        c=widget.get_style_context().get_color(widget.get_state_flags()) if args.gtk=='3.0' else widget.get_color()
        return tuple(round(v*255) for v in (c.red,c.green,c.blue))
    def label(widget):return widget.get_child() if args.gtk=='3.0' else widget.get_first_child()
    def verify():
        try:
            target=Path(args.output)/f'{args.state}.png'
            if args.gtk=='3.0':
                pix=window.get_pixbuf();pix.savev(str(target),'png',[],[])
            else:
                renderer=Gsk.CairoRenderer.new();renderer.realize(None)
                paint=Gtk.WidgetPaintable.new(grid);snap=Gtk.Snapshot();paint.snapshot(snap,grid.get_width(),grid.get_height())
                node=snap.to_node();assert node is not None,'Empty native matrix'
                rect=Graphene.Rect();rect.init(0,0,grid.get_width(),grid.get_height())
                renderer.render_texture(node,rect).save_to_png(str(target));renderer.unrealize()
            image=Image.open(target).convert('RGBA')
            fg=color(label(toggle))
            assert fg==family['selection_foreground'], f'R1: checked label must inherit selected foreground, got {fg}'
            assert color(label(ordinary))==family['foreground'],'Ordinary inactive label changed'
            # Sample inside the gradient, away from glyphs and border. The toggle
            # spans the first two columns; coordinates come from the real widget.
            if args.gtk=='3.0':
                x,y=toggle.translate_coordinates(grid,10,toggle.get_allocated_height()-15)
            else:
                ok,bounds=toggle.compute_bounds(grid);assert ok
                x,y=round(bounds.get_x())+10,round(bounds.get_y()+bounds.get_height())-15
            bg=image.getpixel((x,y))[:3]
            ratio=contrast(fg,bg)
            assert ratio>=4.5,f'R1: checked label contrast {ratio:.2f}:1 on {bg}'
            assert pressed.get_state_flags() & Gtk.StateFlags.ACTIVE, 'Pressed state not applied'
            assert color(label(pressed))==family['selection_foreground'], 'R1: pressed label must inherit selected foreground'
            disabled_label=label(disabled)
            assert disabled_label.get_state_flags() & Gtk.StateFlags.INSENSITIVE
            # Ensure disabled text stays insensitive instead of inheriting the
            # new enabled-toggle foreground override.
            assert color(disabled_label)!=family['selection_foreground'],'Disabled label incorrectly recolored dark'
            backgrounds=0
            for spin,orientation,name,value,sensitive in spins:
                for direction in ('down','up'):
                    insensitive=not sensitive or (direction=='down' and value==0) or (direction=='up' and value==100)
                    if args.gtk=='3.0':
                        # GTK 3 spin arrows are CSS gadgets, not child GtkWidgets.
                        # Render their actual theme background through a node path.
                        path=Gtk.WidgetPath.new();index=path.append_type(Gtk.SpinButton)
                        path.iter_set_object_name(index,'spinbutton');path.iter_add_class(index,orientation)
                        root_state=Gtk.StateFlags.BACKDROP if args.state=='backdrop' else Gtk.StateFlags.NORMAL
                        if not sensitive:root_state|=Gtk.StateFlags.INSENSITIVE
                        path.iter_set_state(index,root_state)
                        index=path.append_type(Gtk.Button);path.iter_set_object_name(index,'button');path.iter_add_class(index,direction)
                        flags=Gtk.StateFlags.BACKDROP if args.state=='backdrop' else Gtk.StateFlags.NORMAL
                        if insensitive:flags|=Gtk.StateFlags.INSENSITIVE
                        path.iter_set_state(index,flags)
                        context=Gtk.StyleContext.new();context.set_path(path);context.set_state(flags)
                        surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,40,36)
                        Gtk.render_background(context,cairo.Context(surface),0,0,40,36)
                        surface.flush();data=bytes(surface.get_data());stride=surface.get_stride()
                        strip={data[y*stride+5*4:y*stride+5*4+4] for y in range(5,31)}
                    else:
                        button=next(w for w in children(spin) if w.get_css_name()=='button' and direction in w.get_css_classes())
                        flags=button.get_state_flags()
                        assert bool(flags & Gtk.StateFlags.INSENSITIVE)==insensitive,(name,direction,'wrong sensitivity')
                        if args.state=='backdrop':assert flags & Gtk.StateFlags.BACKDROP
                        ok,bounds=button.compute_bounds(grid);assert ok
                        x=round(bounds.get_x())+5;y0=round(bounds.get_y())+5;y1=round(bounds.get_y()+bounds.get_height())-5
                        assert y1>y0,(orientation,name,'empty sample')
                        strip={image.getpixel((x,y)) for y in range(y0,y1)}
                    assert len(strip)==1, f'R2: gradient returned for {orientation}/{name}/{direction}/{args.state}: {len(strip)} colors'
                    backgrounds+=1
            result.update({'gtk':args.gtk,'state':args.state,'checked_label':fg,'contrast':round(ratio,2),'flat_spin_backgrounds':backgrounds})
        except BaseException as e:failures.append(e)
        loop.quit();return False
    GLib.timeout_add(300,verify);loop.run();window.destroy()
    if failures:raise failures[0]
    print(json.dumps(result))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gtk',required=True,choices=('3.0','4.0'))
    parser.add_argument('--theme',required=True,type=Path)
    parser.add_argument('--family',choices=tuple(FAMILY_TOOLS['FAMILIES']),default='vapor')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--user-css',type=Path,help='stage a GTK 4 libadwaita overlay for coexistence checks')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--state',choices=('normal','backdrop'),default='normal',help=argparse.SUPPRESS)
    args=parser.parse_args()
    family=FAMILY_TOOLS['get_family'](args.family)
    if args.worker:worker(args);return
    if args.user_css and args.gtk!='4.0':parser.error('--user-css is for GTK 4 only')
    with tempfile.TemporaryDirectory(prefix='vapor-behavior-check-') as name:
        root=Path(name);env=os.environ.copy()
        for variable,folder in (('HOME','home'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_RUNTIME_DIR','runtime'),('XDG_STATE_HOME','state')):
            (root/folder).mkdir(mode=0o700);env[variable]=str(root/folder)
        staged=root/'data/themes'/family['name']
        shutil.copytree(args.theme.resolve(),staged)
        if args.user_css:
            subprocess.run([sys.executable,'-I',str(Path(__file__).resolve().parent/'vapor-libadwaita'),'enable',
                            '--config-home',str(root/'config'),'--profile',str(args.user_css.resolve()),'--json'],
                           capture_output=True,text=True,check=True)
        env.update({'XDG_CONFIG_DIRS':str(root/'config'),'XDG_DATA_DIRS':'/usr/share','GTK_THEME':family['name'],'GDK_BACKEND':'broadway','BROADWAY_DISPLAY':':1','GSK_RENDERER':'cairo','GTK_A11Y':'none','NO_AT_BRIDGE':'1','GTK_MODULES':'','GTK3_MODULES':'','GSETTINGS_BACKEND':'memory','DBUS_SESSION_BUS_ADDRESS':'unix:path=/nonexistent','LC_ALL':'C.UTF-8','GDK_SCALE':'1','GDK_DPI_SCALE':'1'})
        for variable in ('DISPLAY','WAYLAND_DISPLAY','GTK_PATH','GTK_DEBUG','GSK_DEBUG','GDK_DEBUG','GTK_DATA_PREFIX'):env.pop(variable,None)
        daemon='broadwayd' if args.gtk=='3.0' else 'gtk4-broadwayd'
        server=subprocess.Popen([daemon,'-u',str(root/'http.socket'),':1'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            for _ in range(100):
                if (root/'http.socket').exists():break
                if server.poll() is not None:raise RuntimeError(server.communicate())
                time.sleep(.02)
            else:raise RuntimeError('Private display did not start')
            output=args.output.resolve() if args.output else root/'captures';output.mkdir(parents=True,exist_ok=True)
            for state in ('normal','backdrop'):
                command=[sys.executable,'-I',str(Path(__file__).resolve()),'--worker','--gtk',args.gtk,'--theme',str(staged),'--family',args.family,'--state',state,'--output',str(output)]
                if args.user_css:command += ['--user-css',str(args.user_css.resolve())]
                result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=15)
                if result.returncode or result.stderr:raise RuntimeError(result.stdout+result.stderr)
                print(result.stdout.strip())
        finally:server.terminate();server.communicate(timeout=5)
    print(f'GTK {args.gtk} inactive labels and spin background regressions: PASS')


if __name__=='__main__':main()
