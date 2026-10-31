#!/usr/bin/env python3
"""Audit real VGUI2 Adw controls using paired unfocused/focused snapshots.

Uses private HOME/XDG, Broadway and Cairo; no desktop input or app actions.
Native geometry, semantic buttons and light/high-contrast fallbacks are paired
with stock Adwaita. Called by the standard GTK 4 suite for the VGUI2 family.
"""
import argparse
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
NATIVE=runpy.run_path(str(ROOT/'tools/check-libadwaita.py'))


def worker(args):
    import warnings
    warnings.filterwarnings('ignore',category=DeprecationWarning)
    import gi
    for name,version in (('Gtk','4.0'),('Adw','1'),('Gsk','4.0'),('Graphene','1.0')):
        gi.require_version(name,version)
    from gi.repository import Gtk,Adw,GLib,Gsk,Graphene
    from PIL import Image
    assert (Gtk.get_major_version(),Gtk.get_minor_version())>=(4,24),'GTK 4.24+ required'
    assert (Adw.get_major_version(),Adw.get_minor_version())>=(1,10),'libadwaita 1.10+ required'
    Adw.init()
    manager=Adw.StyleManager.get_default()
    manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT if args.light else Adw.ColorScheme.FORCE_DARK)
    assert manager.get_dark()==(not args.light),'ADW-CONTROLS: requested appearance was not applied'
    assert manager.get_high_contrast()==args.hc,'ADW-CONTROLS: requested contrast was not applied'
    settings=Gtk.Settings.get_default()
    settings.set_property('gtk-enable-animations',False)
    settings.set_property('gtk-cursor-blink',False)
    assert settings.get_property('gtk-theme-name')=='Adwaita-empty','ADW-CONTROLS: native providers disabled'
    Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL if args.rtl else Gtk.TextDirection.LTR)
    window=Adw.Window(title='VGUI2 libadwaita control audit')
    window.set_default_size(560,180)
    window.set_content(Gtk.Box())
    assert window.get_direction()==(Gtk.TextDirection.RTL if args.rtl else Gtk.TextDirection.LTR),'ADW-CONTROLS: requested direction was not applied'
    samples=[]

    def descendants(widget):
        yield widget
        child=widget.get_first_child()
        while child:
            yield from descendants(child);child=child.get_next_sibling()

    def button(label,style=None):
        widget=Gtk.Button(label=label)
        if style:widget.add_css_class(style)
        return widget

    def add(name,widget,column,row,target=None,semantic=False):
        holder=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,margin_start=20,margin_end=20,
                       margin_top=20,margin_bottom=20,valign=Gtk.Align.START)
        if column:holder.add_css_class('card')
        # Padding is an actual widget margin, not a style override.
        inner=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,margin_start=10,margin_end=10,
                      margin_top=6,margin_bottom=6)
        inner.append(widget);holder.append(inner)
        samples.append((('card/' if column else 'window/')+name,target or widget,semantic,holder))

    for column in (0,1):
        add('ordinary',button('Ordinary'),column,0)
        add('flat',button('Flat','flat'),column,1)
        add('suggested',button('Suggested','suggested-action'),column,2)
        add('checked',Gtk.ToggleButton(label='Checked',active=True),column,3)
        add('check',Gtk.CheckButton(label='Checked control',active=True),column,4)
        add('switch',Gtk.Switch(active=True,halign=Gtk.Align.START),column,5)
        add('entry',Gtk.Entry(text='Entry focus'),column,6)
        add('spin',Gtk.SpinButton.new_with_range(0,100,1),column,7)
        add('link',Gtk.LinkButton(uri='https://example.invalid',label='Link button'),column,8)
        action=Adw.ActionRow(title='Activatable action row');action.set_activatable(True);action.set_focusable(True)
        rows=Gtk.ListBox();rows.add_css_class('boxed-list');rows.append(action)
        add('action-row',rows,column,9,target=action)
        entry=Adw.EntryRow(title='Native entry row',text='Entry row focus')
        rows=Gtk.ListBox();rows.add_css_class('boxed-list');rows.append(entry)
        add('entry-row',rows,column,10,target=entry)
        add('destructive',button('Destructive','destructive-action'),column,11,semantic=True)
        menu=Gtk.MenuButton(label='Destructive menu');menu.add_css_class('destructive-action')
        menu.set_popover(Gtk.Popover(child=Gtk.Label(label='Not opened')))
        add('destructive-menu',menu,column,12,target=menu.get_first_child(),semantic=True)
        split=Adw.SplitButton(label='Destructive split');split.add_css_class('destructive-action')
        split.set_popover(Gtk.Popover(child=Gtk.Label(label='Not opened')))
        main=next(w for w in descendants(split) if isinstance(w,Gtk.Button))
        add('destructive-split',split,column,13,target=main,semantic=True)
        split_menu=Adw.SplitButton(label='Destructive split menu');split_menu.add_css_class('destructive-action')
        split_menu.set_popover(Gtk.Popover(child=Gtk.Label(label='Not opened')))
        arrow=next(w for w in descendants(split_menu) if isinstance(w,Gtk.MenuButton)).get_first_child()
        add('destructive-split-menu',split_menu,column,14,target=arrow,semantic=True)
        spinrow=Adw.SpinRow.new_with_range(0,100,1);spinrow.set_title('Native spin row')
        rows=Gtk.ListBox();rows.add_css_class('boxed-list');rows.append(spinrow)
        add('spin-row',rows,column,15,target=spinrow)
        for row,state,flag in ((16,'hover',Gtk.StateFlags.PRELIGHT),(17,'pressed',Gtk.StateFlags.ACTIVE)):
            checked=Gtk.ToggleButton(label='Checked '+state,active=True);checked.set_state_flags(flag,False)
            add('checked-'+state,checked,column,row)
        nested=Gtk.ToggleButton(active=True);box=Gtk.Box();box.append(Gtk.Label(label='Nested checked label',hexpand=True))
        nested.set_child(box);add('checked-nested',nested,column,18)
        checked_semantic=Gtk.ToggleButton(label='Destructive checked',active=True)
        checked_semantic.add_css_class('destructive-action')
        add('destructive-checked',checked_semantic,column,19,semantic=True)
        for state,flag in (('hover',Gtk.StateFlags.PRELIGHT),('pressed',Gtk.StateFlags.ACTIVE)):
            ordinary=button('Ordinary '+state);ordinary.set_state_flags(flag,False)
            add('ordinary-'+state,ordinary,column,20)
        keyboard=button('Keyboard activating');keyboard.add_css_class('keyboard-activating')
        add('ordinary-keyboard',keyboard,column,21)
        osd=Gtk.ToggleButton(label='Checked OSD',active=True);osd.add_css_class('osd')
        add('osd-checked',osd,column,22)
        active_link=Gtk.LinkButton(uri='https://example.invalid',label='Active link')
        active_link.set_state_flags(Gtk.StateFlags.ACTIVE,False);add('active-link',active_link,column,23)

    renderer=Gsk.CairoRenderer.new();renderer.realize(None)
    failures=[];records=[];loop=GLib.MainLoop();index=0;base=None;parking=None
    active=not args.baseline and manager.get_dark() and not manager.get_high_contrast()
    window.present()

    def snapshot(name):
        assert window.get_scale_factor()==args.scale,'ADW-CONTROLS: wrong native scale'
        width,height=window.get_width(),window.get_height()
        snap=Gtk.Snapshot();snap.scale(args.scale,args.scale)
        snap.render_background(window.get_style_context(),0,0,width,height)
        Gtk.WidgetPaintable.new(window).snapshot(snap,width,height)
        node=snap.to_node();assert node is not None,'ADW-CONTROLS: empty snapshot'
        rect=Graphene.Rect();rect.init(0,0,width*args.scale,height*args.scale)
        path=args.output/(name+'.png')
        assert renderer.render_texture(node,rect).save_to_png(str(path))
        with Image.open(path) as image:return image.convert('RGB')

    def guard(function):
        def guarded():
            try:function()
            except BaseException as error:failures.append(error);loop.quit()
            return False
        return guarded

    def clear():
        nonlocal parking
        if index==len(samples):loop.quit();return
        window.set_focus_visible(False)
        page=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        parking=Gtk.Button(label='Focus parking')
        page.append(parking);page.append(samples[index][3]);window.set_content(page)
        parking.grab_focus()
        GLib.timeout_add(60,guard(start))

    def start():
        nonlocal base
        name,widget,_semantic,_holder=samples[index]
        assert not any(w.get_state_flags() & Gtk.StateFlags.FOCUS_VISIBLE for w in descendants(widget)),'ADW-CONTROLS: baseline already has visible focus '+name
        base=snapshot(f'{index:02}-base')
        assert widget.grab_focus(),'ADW-CONTROLS: cannot focus '+name
        window.set_focus_visible(True)
        GLib.timeout_add(80,guard(check))

    def check():
        nonlocal index
        name,widget,semantic,_holder=samples[index]
        focused=snapshot(f'{index:02}-focus')
        assert focused.size==base.size,'ADW-CONTROLS: focus changed window allocation'
        assert any(w.get_state_flags() & Gtk.StateFlags.FOCUS_VISIBLE for w in descendants(widget)),'ADW-CONTROLS: no visible focus '+name
        ok,bounds=widget.compute_bounds(window);assert ok
        x=round(bounds.get_x()*args.scale);y=round(bounds.get_y()*args.scale)
        width=round(bounds.get_width()*args.scale);height=round(bounds.get_height()*args.scale)
        changed=[];s=args.scale
        # Real before/after pixels include inset and outside outlines. Limit to
        # the middle of each edge to exclude text, caret and corner antialiasing.
        coordinates=set()
        for px in range(max(0,x-5*s),min(focused.width,x+width+5*s)):
            if x+6*s<=px<x+width-6*s:
                for py in (*range(max(0,y-5*s),y+4*s),*range(y+height-4*s,min(focused.height,y+height+5*s))):coordinates.add((px,py))
        for py in range(max(0,y+6*s),min(focused.height,y+height-6*s)):
            for px in (*range(max(0,x-5*s),x+4*s),*range(x+width-4*s,min(focused.width,x+width+5*s))):coordinates.add((px,py))
        for point in coordinates:
            a=focused.getpixel(point);b=base.getpixel(point)
            if a!=b:changed.append(NATIVE['contrast'](a,b))
        ratio=max(changed,default=1)
        text_pair=None
        if isinstance(widget,Gtk.Button):
            label=next((w for w in descendants(widget) if isinstance(w,Gtk.Label)),None)
            if label:
                color=label.get_color()
                background=focused.getpixel((x+9*s,y+height//2))
                ink=[round(255*max(0,min(1,v))*color.alpha+background[i]*(1-color.alpha))
                     for i,v in enumerate((color.red,color.green,color.blue))]
                text_ratio=NATIVE['contrast'](ink,background)
                text_pair={'foreground':ink,'background':list(background),'contrast':round(text_ratio,4),'pass':text_ratio>=4.5}
        semantic_focus=None
        if semantic:
            outline=Gtk.Snapshot();outline.scale(s,s);point=Graphene.Point();point.init(6,6);outline.translate(point)
            outline.render_focus(widget.get_style_context(),0,0,widget.get_width(),widget.get_height())
            node=outline.to_node();assert node is not None,'ADW-CONTROLS: missing semantic focus '+name
            rect=Graphene.Rect();rect.init(0,0,(widget.get_width()+12)*s,(widget.get_height()+12)*s)
            path=args.output/f'{index:02}-semantic-focus.png'
            renderer.render_texture(node,rect).save_to_png(str(path))
            with Image.open(path) as layer:semantic_focus=hashlib.sha256(layer.convert('RGBA').tobytes()).hexdigest()
        records.append({'name':name,'semantic':semantic,'focus_contrast':round(ratio,4),
                        'focus_pass':ratio>=3,
                        'changed_pixels':len(changed),'geometry':[width,height],
                        'css_classes':list(widget.get_css_classes()),'text':text_pair,
                        'semantic_focus_sha256':semantic_focus,
                        'focus_image_sha256':hashlib.sha256(focused.tobytes()).hexdigest()})
        # Complete the diagnostic matrix before reporting all weak controls.
        index+=1;GLib.timeout_add(40,guard(clear))

    GLib.timeout_add(300,guard(clear));loop.run();window.destroy();renderer.unrealize()
    if failures:raise failures[0]
    result={'gtk':f'{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}',
            'adwaita':f'{Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}',
            'baseline':args.baseline,'active':active,'scale':args.scale,'rtl':args.rtl,
            'dark':manager.get_dark(),'high_contrast':manager.get_high_contrast(),'controls':records}
    (args.output/'controls.json').write_text(json.dumps(result,indent=2)+'\n')
    if active:
        unreadable=[(r['name'],r['text']['contrast']) for r in records if not r['semantic'] and r['text'] and not r['text']['pass']]
        assert not unreadable,'ADW-CONTROL-TEXT: '+str(unreadable)
        weak=[(r['name'],r['focus_contrast']) for r in records if not r['semantic'] and not r['focus_pass']]
        assert not weak,'ADW-CONTROL-FOCUS: '+str(weak)
    print(json.dumps(result))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',type=Path,default=ROOT/'libadwaita/vgui2.css')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--baseline',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--light',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--hc',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--rtl',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--scale',type=int,choices=(1,2),default=1,help=argparse.SUPPRESS)
    args=parser.parse_args()
    if args.worker:worker(args);return
    helpers=runpy.run_path(str(ROOT/'tools/check-widget-factory.py'))
    client=runpy.run_path(str(ROOT/'tools/broadway-test-client.py'))['FrameClient']
    with tempfile.TemporaryDirectory(prefix='vgui2-adw-controls-') as folder:
        scratch=Path(folder);output=args.output.resolve() if args.output else scratch/'evidence';output.mkdir(parents=True,exist_ok=True)
        (output/'results.json').unlink(missing_ok=True)
        results=[]
        states=[(False,False,False,1)]
        if not args.quick:states += [(True,False,False,1),(False,True,False,1),(True,True,False,1),(False,False,True,1),(False,False,False,2)]
        if args.light:states=[(True,False,False,1)]
        elif args.hc:states=[(False,True,False,1)]
        for light,hc,rtl,scale in states:
            paired=[]
            for baseline in (True,False):
                name=('light' if light else 'dark')+('-hc' if hc else '')+('-rtl' if rtl else '')+f'-s{scale}-'+('base' if baseline else 'vgui2')
                directory=scratch/name;directory.mkdir();target=output/name;target.mkdir(exist_ok=True)
                options=argparse.Namespace(profile=args.profile,family='vgui2',scale=scale,hc=hc)
                env,bus=NATIVE['make_environment'](directory,options,not baseline)
                command=['dbus-run-session','--config-file='+str(bus),'--',sys.executable,'-I',str(Path(__file__).resolve()),
                         '--worker','--profile',str(args.profile.resolve()),'--output',str(target),'--scale',str(scale)]
                for flag,value in (('--baseline',baseline),('--light',light),('--hc',hc),('--rtl',rtl)):
                    if value:command.append(flag)
                with helpers['private_display'](directory,env,target),client(directory/'http.socket',scale):
                    code,stdout,stderr=helpers['run_application'](command,env,target,'worker')
                unexpected=[line for line in stderr.splitlines() if line.strip() and not NATIVE['BROADWAY_WARNING'].fullmatch(line)]
                if code or unexpected:raise RuntimeError(name+'\n'+stdout+'\n'+stderr)
                data=json.loads(stdout);data['case']=name
                data['known_broadway_warnings']=[line for line in stderr.splitlines() if NATIVE['BROADWAY_WARNING'].fullmatch(line)]
                paired.append(data);results.append(data)
                print('VGUI2 Adw controls '+name+': PASS',flush=True)
            for before,after in zip(paired[0]['controls'],paired[1]['controls'],strict=True):
                assert before['name']==after['name'] and before['geometry']==after['geometry'],'ADW-CONTROL-GEOMETRY: '+before['name']
                if before['semantic']:
                    assert before['semantic_focus_sha256']==after['semantic_focus_sha256'],'ADW-CONTROL-SEMANTIC: '+before['name']
                    if before['text']:
                        assert before['text']['foreground']==after['text']['foreground'],'ADW-CONTROL-SEMANTIC: ink '+before['name']
                if not paired[1]['active']:
                    assert before['focus_image_sha256']==after['focus_image_sha256'],'ADW-CONTROL-GUARD: '+before['name']
        (output/'results.json').write_text(json.dumps({'cases':results,'native_renderer':'Broadway','snapshot_renderer':'Cairo',
            'profile_sha256':hashlib.sha256(args.profile.read_bytes()).hexdigest()},indent=2)+'\n')
        print(f'VGUI2 Adw real-control audit: PASS ({len(results)} cases)',flush=True)


if __name__=='__main__':main()
