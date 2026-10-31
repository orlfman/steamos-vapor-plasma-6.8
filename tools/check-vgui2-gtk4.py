#!/usr/bin/env python3
"""Check real VGUI2 GTK 4 surfaces, states, focus, glyphs and popup windows.

All settings, files, D-Bus and displays are private. No desktop input is sent.
The standard check-gtk4.py invokes this after native/Widget Factory stages.
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

ROOT=Path(__file__).resolve().parent.parent
FAMILY=runpy.run_path(str(ROOT/'tools/theme-families.py'))['get_family']('vgui2')
TransportClient=runpy.run_path(str(ROOT/'tools/broadway-test-client.py'))['FrameClient']


class FrameClient(TransportClient):
    """Acknowledge frames at display cadence instead of spinning the GTK clock."""
    def event(self,operation,*arguments):
        if operation==14:
            delay=getattr(self,'next_frame',0)-time.monotonic()
            if delay>0:time.sleep(delay)
            self.next_frame=time.monotonic()+1/60
        super().event(operation,*arguments)


private_display=runpy.run_path(str(ROOT/'tools/check-widget-factory.py'))['private_display']
# Both messages reproduced with stock GTK, no project CSS, in timing-control.py
# (see gtk4port.md). Retain/count only these transport warnings; never CSS errors.
TIMING_WARNING=re.compile(r'\(process:\d+\): Gdk-WARNING \*\*: [\d:.]+: '
    r'(?:Duplicate call to gdk_frame_timings_submitted\(\) with different values\.|'
    r'gdk_frame_timings_submitted\(\) called on submitted frame\.)')


def contrast(a,b):
    def luminance(rgb):
        return sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4)
                   for w,v in zip((.2126,.7152,.0722),rgb))
    low,high=sorted((luminance(a),luminance(b)))
    return (high+.05)/(low+.05)


def worker(args):
    import warnings
    warnings.filterwarnings('ignore',category=DeprecationWarning)
    import gi
    for name,version in (('Gtk','4.0'),('Gsk','4.0'),('Graphene','1.0')):gi.require_version(name,version)
    from gi.repository import Gtk,Gdk,Gio,GLib,Gsk,Graphene
    from PIL import Image
    Gtk.init()
    assert (Gtk.get_major_version(),Gtk.get_minor_version())>=(4,24),'GTK 4.24+ required'
    # Construct in the requested direction, avoiding a live LTR-to-RTL
    # relayout of the private Broadway surface before its initial frame.
    Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL if args.state=='rtl' else Gtk.TextDirection.LTR)
    settings=Gtk.Settings.get_default()
    assert settings.get_property('gtk-theme-name')==FAMILY['name'],'GTK4-DISCOVERY: wrong named theme'
    settings.set_property('gtk-interface-color-scheme',Gtk.InterfaceColorScheme.DARK if args.dark else Gtk.InterfaceColorScheme.LIGHT)
    settings.set_property('gtk-enable-animations',False)
    settings.set_property('gtk-cursor-blink',False)
    errors=[]
    for css in sorted((args.theme/'gtk-4.0').glob('*.css')):
        provider=Gtk.CssProvider()
        provider.connect('parsing-error',lambda _p,_s,error:errors.append(error.message))
        provider.load_from_path(str(css))
    assert not errors,'GTK4-CSS: '+str(errors)
    window=Gtk.Window(title='VGUI2 Classic GTK 4 state audit')
    context=window.get_style_context()
    assert context.lookup_color('vgui4_fixture_marker')[0],'GTK4-DISCOVERY: staged copy not loaded'
    assert context.lookup_color('vgui4_dark_fixture_marker')[0]==args.dark,'GTK4-VARIANT: wrong normal/dark entry'
    for role,expected in (('theme_bg_color',FAMILY['window']),('theme_selected_bg_color',FAMILY['selection']),
                          ('theme_selected_fg_color',FAMILY['selection_foreground'])):
        found,value=context.lookup_color(role)
        assert found and tuple(round(v*255) for v in (value.red,value.green,value.blue))==expected,'GTK4-PALETTE: '+role
    renderer=Gsk.CairoRenderer.new();renderer.realize(None)
    body=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_start=14,margin_end=14,margin_top=14,margin_bottom=14)
    window.set_child(body)
    grid=Gtk.Grid(column_spacing=12,row_spacing=8);body.append(grid)
    samples=[];focus=[];indicators=[];notebooks=[];arrow_checks=[]
    painted_window=None
    report={'gtk':f'{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}',
            'state':args.state,'dark':args.dark,'display_scale':args.scale,'labels':[],'focus':[],'indicators':[],'notebooks':[],'popups':[]}
    failures=[];loop=GLib.MainLoop()

    def descendants(widget):
        yield widget
        child=widget.get_first_child()
        while child:
            yield from descendants(child);child=child.get_next_sibling()

    def snapshot(widget,name):
        width,height=widget.get_width(),widget.get_height()
        assert width>0 and height>0,(name,'empty allocation')
        snap=Gtk.Snapshot();snap.scale(args.scale,args.scale)
        Gtk.WidgetPaintable.new(widget).snapshot(snap,width,height)
        node=snap.to_node();assert node is not None,(name,'empty snapshot')
        rect=Graphene.Rect();rect.init(0,0,width*args.scale,height*args.scale)
        path=args.output/(name+'.png')
        assert renderer.render_texture(node,rect).save_to_png(str(path))
        with Image.open(path) as source:return source.convert('RGBA')

    def color(widget):
        value=widget.get_color()
        return [value.red,value.green,value.blue,value.alpha]

    def symbolic_image(widget,icon,name,size=16):
        paintable=Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).lookup_icon(
            icon,None,size,args.scale,widget.get_direction(),Gtk.IconLookupFlags.FORCE_SYMBOLIC)
        snap=Gtk.Snapshot();snap.scale(args.scale,args.scale)
        white=Gdk.RGBA();white.parse('white')
        paintable.snapshot_symbolic(snap,size,size,[white])
        node=snap.to_node();assert node is not None
        rect=Graphene.Rect();rect.init(0,0,size*args.scale,size*args.scale)
        target=args.output/('reference-'+name+'.png')
        renderer.render_texture(node,rect).save_to_png(str(target))
        with Image.open(target) as source:return source.convert('RGBA')

    def style_focus(widget,reference,name):
        actual=snapshot(widget,name+'-focus')
        base=snapshot(reference,name+'-base')
        assert actual.size==base.size,'GTK4-CONTROLS: focus changed title allocation'
        under=Image.new('RGBA',actual.size,(*FAMILY['window'],255))
        actual=Image.alpha_composite(under,actual);base=Image.alpha_composite(under,base)
        changed=[contrast([v/255 for v in a[:3]],[v/255 for v in b[:3]])
                 for a,b in zip(actual.get_flattened_data(),base.get_flattened_data()) if a!=b]
        return max(changed,default=1)

    def append_sample(name,label,disabled=False):samples.append((name,label,disabled))

    controls=Gtk.Box(spacing=8)
    grid.attach(controls,0,0,2,1)
    for name,style,checked,pressed in (('Ordinary','',False,False),('Checked','',True,False),
            ('Pressed','',False,True),('Suggested','suggested-action',False,False),
            ('Destructive','destructive-action',False,True)):
        button=Gtk.ToggleButton(label=name,active=checked) if checked else Gtk.Button(label=name)
        if style:button.add_css_class(style)
        if pressed:button.set_state_flags(Gtk.StateFlags.ACTIVE,False)
        controls.append(button);append_sample(name,button.get_child())
        focus.append((name,button))
    entry=Gtk.Entry(text='Editable text')
    grid.attach(entry,0,1,1,1);focus.append(('Entry',entry))
    switch=Gtk.Switch(active=True,halign=Gtk.Align.START)
    grid.attach(switch,1,1,1,1);focus.append(('Checked-switch',switch))
    for column,kind in enumerate(('list','flow')):
        box=Gtk.Box(spacing=8)
        label=Gtk.Label(label='Selected '+kind,margin_start=8,margin_end=8)
        button=Gtk.Button(label='Nested button');box.append(label);box.append(button)
        if kind=='list':
            container=Gtk.ListBox();container.append(box);selected=container.get_row_at_index(0);container.select_row(selected)
        else:
            container=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.SINGLE)
            container.insert(box,-1);selected=container.get_child_at_index(0);container.select_child(selected)
        grid.attach(container,column,2,1,1)
        append_sample(kind,label);append_sample(kind+'-button',button.get_child());focus.append((kind,selected))
    for row,(kind,view_type) in enumerate((('listview',Gtk.ListView),('columnview',Gtk.ColumnView),('gridview',Gtk.GridView)),3):
        factory=Gtk.SignalListItemFactory()
        def setup(_factory,item,kind=kind):
            box=Gtk.Box(spacing=8)
            label=Gtk.Label(label='Selected '+kind,margin_start=8,margin_end=8)
            button=Gtk.Button(label='Nested button');box.append(label);box.append(button)
            item.set_child(box);append_sample(kind,label);append_sample(kind+'-button',button.get_child())
        factory.connect('setup',setup)
        model=Gtk.SingleSelection.new(Gtk.StringList.new(['Selected']))
        if kind=='columnview':
            view=view_type(model=model);view.append_column(Gtk.ColumnViewColumn(title='Column',factory=factory))
        else:view=view_type(model=model,factory=factory)
        grid.attach(view,0,row,2,1)
    for row,kind in enumerate(('info','warning','error','question'),6):
        bar=Gtk.InfoBar(message_type=getattr(Gtk.MessageType,kind.upper()))
        label=Gtk.Label(label=kind+' message',margin_start=8,margin_end=8)
        bar.add_child(label);grid.attach(bar,0,row,2,1);append_sample(kind,label)
    disabled_box=Gtk.ListBox()
    disabled_label=Gtk.Label(label='Disabled selected row',margin_start=8,margin_end=8)
    disabled_box.append(disabled_label);disabled_row=disabled_box.get_row_at_index(0)
    disabled_box.select_row(disabled_row);disabled_row.set_sensitive(False)
    grid.attach(disabled_box,0,10,2,1);append_sample('disabled-selected',disabled_label,True)
    glyph_box=Gtk.Box(spacing=8);grid.attach(glyph_box,0,11,2,1)
    reference=Gtk.CssProvider()
    reference.load_from_string('.vgui-blank check, .vgui-blank radio { -gtk-icon-source: none; }\n.vgui-empty-arrow { background-image: none; }')
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),reference,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    for kind in ('check','radio'):
        for state in ('unchecked','checked','mixed','checked-hover','mixed-hover','checked-disabled','mixed-disabled'):
            pair=[]
            for blank in (False,True):
                button=Gtk.CheckButton(active=state.startswith('checked'),inconsistent=state.startswith('mixed'))
                if kind=='radio':button.set_group(Gtk.CheckButton())
                if blank:button.add_css_class('vgui-blank')
                if state.endswith('disabled'):button.set_sensitive(False)
                glyph_box.append(button);pair.append(button)
            indicators.append((kind,state,pair))
    notebook_box=Gtk.Box(spacing=8);body.append(notebook_box)
    for position in ('top','bottom','left','right'):
        notebook=Gtk.Notebook(scrollable=True)
        notebook.set_tab_pos(getattr(Gtk.PositionType,position.upper()))
        notebook.set_size_request(165,150)
        for i in range(16):notebook.append_page(Gtk.Label(label='Page'),Gtk.Label(label='Tab '+str(i+1)))
        notebook_box.append(notebook);notebooks.append((position,notebook))
    actions=Gio.SimpleActionGroup()
    actions.add_action(Gio.SimpleAction.new('action',None))
    actions.add_action(Gio.SimpleAction.new_stateful('checked',None,GLib.Variant.new_boolean(True)))
    window.insert_action_group('test',actions)
    menu=Gio.Menu();menu.append('Menu item','test.action');menu.append('Checked item','test.checked')
    popover=Gtk.PopoverMenu.new_from_model(menu)
    menu_button=Gtk.MenuButton(label='Popup menu',popover=popover)
    dropdown=Gtk.DropDown.new_from_strings(['First item','Second item'])
    body.append(menu_button);body.append(dropdown)
    audit_tools=runpy.run_path(str(ROOT/'tools/gtk4-audit-checks.py'))
    verify_controls,selection_steps,apply_controls=audit_tools['build'](Gtk,body)
    window.present()

    def guard(function):
        def wrapped(*args):
            try:return function(*args)
            except BaseException as error:
                failures.append(error);loop.quit();return False
        return wrapped

    def apply_state():
        window.set_focus(None)
        for widget in descendants(window):
            widget.set_direction(Gtk.TextDirection.RTL if args.state=='rtl' else Gtk.TextDirection.LTR)
            if args.state=='backdrop':widget.set_state_flags(Gtk.StateFlags.BACKDROP,False)
            else:widget.unset_state_flags(Gtk.StateFlags.BACKDROP)
        for _kind,state,pair in indicators:
            if state.endswith('hover'):
                for button in pair:
                    button.set_state_flags(Gtk.StateFlags.PRELIGHT,False)
                    button.get_first_child().set_state_flags(Gtk.StateFlags.PRELIGHT,False)
        apply_controls()
        GLib.timeout_add(150,guard(verify));return False

    def verify():
        nonlocal painted_window
        assert window.get_scale_factor()==args.scale
        image=snapshot(window,'states')
        painted_window=image
        # The top-left pixel belongs to the automatically supplied titlebar.
        # Sample the empty client-area padding at the bottom instead.
        assert image.getpixel((5*args.scale,image.height-5*args.scale))[:3]==FAMILY['window'],'GTK4-SURFACE: actual window background'
        report['audit_controls']=verify_controls(window,image,snapshot,symbolic_image,style_focus,args.scale,args.output)
        problems=[]
        paths={}
        for name,label,disabled in samples:
            parent=label;path=[]
            while parent and parent is not window:
                path.append([parent.get_css_name(),list(parent.get_css_classes()),int(parent.get_state_flags())]);parent=parent.get_parent()
            paths[name]=path
            assert bool(label.get_state_flags() & Gtk.StateFlags.BACKDROP)==(args.state=='backdrop'),(name,'wrong backdrop state')
            ok,bounds=label.compute_bounds(window);assert ok
            point=(round(bounds.get_x()-2)*args.scale,round(bounds.get_y()+bounds.get_height()/2)*args.scale)
            bg=image.getpixel(point);fg=color(label)
            assert bg[3]==255,(name,'transparent background',bg)
            composite=[v*fg[3]+b/255*(1-fg[3]) for v,b in zip(fg,bg)]
            ratio=contrast(composite,[v/255 for v in bg[:3]])
            passed=fg[3]<1 if disabled else ratio>=4.5
            result={'name':name,'foreground':fg,'painted_background':list(bg),'contrast':round(ratio,3),'disabled':disabled,'passed':passed}
            report['labels'].append(result)
            if not passed:problems.append(result)
        (args.output/'label-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
        assert not problems,'GTK4-LABELS: '+json.dumps(problems)
        artwork={}
        for kind,state,pair in indicators:
            actual=snapshot(pair[0].get_first_child(),kind+'-'+state)
            blank=snapshot(pair[1].get_first_child(),kind+'-'+state+'-blank')
            assert (actual.tobytes()!=blank.tobytes())==(state!='unchecked'),'GTK4-GLYPH: '+kind+' '+state
            artwork[kind,state]=actual.tobytes()
            report['indicators'].append({'kind':kind,'state':state,'size':list(actual.size),'passed':True})
        for kind in ('check','radio'):
            for suffix in ('','-hover','-disabled'):
                assert artwork[kind,'checked'+suffix]!=artwork[kind,'mixed'+suffix],'GTK4-GLYPH: indistinguishable '+kind+suffix
        for position,notebook in notebooks:
            arrows=[w for w in descendants(notebook) if w.get_css_name()=='arrow']
            assert len(arrows)==2,(position,'missing arrows')
            for arrow in arrows:
                is_start='down' in arrow.get_css_classes()
                horizontal_start='pan-end-symbolic' if args.state=='rtl' else 'pan-start-symbolic'
                horizontal_end='pan-start-symbolic' if args.state=='rtl' else 'pan-end-symbolic'
                icon=('pan-up-symbolic' if is_start else 'pan-down-symbolic') if position in ('left','right') else (horizontal_start if is_start else horizontal_end)
                child=arrow.get_child()
                assert isinstance(child,Gtk.Image),'GTK4-NOTEBOOK: missing image child'
                actual=snapshot(arrow,'arrow-'+position+('-start' if is_start else '-end'))
                # Render an independent themed symbolic icon, bypassing widget
                # CSS entirely. Compare normalized alpha masks so disabled
                # opacity cannot hide a rotated/replaced/missing glyph.
                reference=symbolic_image(child,icon,position+'-'+icon)
                record={'position':position,'icon':icon}
                report['notebooks'].append(record)
                arrow_checks.append((arrow,actual,reference,record))
                arrow.add_css_class('vgui-empty-arrow')
        GLib.timeout_add(100,guard(verify_arrows));return False

    def verify_arrows():
        for arrow,actual,reference,record in arrow_checks:
            empty=snapshot(arrow,'empty-'+record['position']+'-'+record['icon'])
            size=16*args.scale
            x=(actual.width-size)//2;y=(actual.height-size)//2
            a=actual.crop((x,y,x+size,y+size));b=empty.crop((x,y,x+size,y+size))
            mask=[max(abs(p-q) for p,q in zip(px[:3],py[:3])) for px,py in zip(a.get_flattened_data(),b.get_flattened_data())]
            expected=list(reference.getchannel('A').get_flattened_data())
            assert max(mask)>0 and max(expected)>0,'GTK4-NOTEBOOK: blank arrow'
            # CSS recoloring and disabled opacity alter antialiased edge
            # intensities. Compare occupied glyph pixels rather than colors.
            def logical_support(values):
                peak=max(values);logical=[]
                for y in range(16):
                    for x in range(16):
                        logical.append(sum(values[(y*args.scale+dy)*size+x*args.scale+dx]/peak
                                           for dy in range(args.scale) for dx in range(args.scale))/args.scale**2)
                return {i for i,value in enumerate(logical) if value>.2}
            occupied=logical_support(mask);wanted=logical_support(expected)
            overlap=len(occupied&wanted)/len(occupied|wanted)
            assert overlap>=.85,'GTK4-NOTEBOOK: '+record['position']+' '+record['icon']+' '+str(overlap)
            record.update({'glyph_support_iou':round(overlap,5),'passed':True})
            arrow.remove_css_class('vgui-empty-arrow')
        GLib.timeout_add(100,guard(selection_next));return False

    selection_index=0
    report['text_selections']=[]
    def selection_next():
        if selection_index==len(selection_steps):
            GLib.timeout_add(100,guard(focus_base));return False
        _name,apply,_check=selection_steps[selection_index]
        apply();GLib.timeout_add(100,guard(selection_verify));return False

    def selection_verify():
        nonlocal selection_index
        name,_apply,check=selection_steps[selection_index]
        report['text_selections'].append(check(window,snapshot(window,'selection-'+name),args.scale))
        selection_index+=1;GLib.timeout_add(50,guard(selection_next));return False

    focus_index=0;baseline=None;focus_background=None
    def focus_base():
        nonlocal baseline
        if focus_index==len(focus):
            popover.popup();GLib.timeout_add(150,guard(popup_menu));return False
        name,widget=focus[focus_index]
        window.set_focus(None)
        widget.unset_state_flags(Gtk.StateFlags.FOCUS_VISIBLE|Gtk.StateFlags.FOCUSED|Gtk.StateFlags.FOCUS_WITHIN)
        GLib.timeout_add(80,guard(focus_start));return False

    def focus_start():
        nonlocal baseline,focus_background
        name,widget=focus[focus_index];baseline=snapshot(widget,'focus-'+name+'-base')
        ok,bounds=widget.compute_bounds(window);assert ok
        point=(max(0,round(bounds.get_x()-1)*args.scale),round(bounds.get_y()+bounds.get_height()/2)*args.scale)
        focus_background=painted_window.getpixel(point)
        assert focus_background[3]==255,'GTK4-FOCUS: transparent parent sample'
        widget.grab_focus()
        widget.set_state_flags(Gtk.StateFlags.FOCUS_VISIBLE|Gtk.StateFlags.FOCUSED,False)
        GLib.timeout_add(80,guard(focus_verify));return False

    def focus_verify():
        nonlocal focus_index
        name,widget=focus[focus_index];image=snapshot(widget,'focus-'+name)
        assert image.size==baseline.size,'GTK4-FOCUS: focus changed allocation'
        # Transparent containers paint their outline over their parent's fill.
        # Include those pixels after compositing onto the sampled real backdrop.
        under=Image.new('RGBA',image.size,focus_background)
        image=Image.alpha_composite(under,image)
        base=Image.alpha_composite(under,baseline)
        # Sample the outline's interior band. Exclude caret/text focus changes.
        pixels=[];width,height=image.size;s=args.scale
        for y in range(2*s,height-2*s):
            for x in range(2*s,width-2*s):
                if min(x,y,width-1-x,height-1-y)>5*s:continue
                a=image.getpixel((x,y));b=base.getpixel((x,y))
                if a!=b and a[3]==255 and b[3]==255:
                    pixels.append(contrast([v/255 for v in a[:3]],[v/255 for v in b[:3]]))
        ratio=max(pixels,default=1)
        assert ratio>=3,'GTK4-FOCUS: '+name+' '+str(ratio)
        report['focus'].append({'name':name,'contrast':round(ratio,3),'changed_pixels':len(pixels)})
        focus_index+=1;GLib.timeout_add(50,guard(focus_base));return False

    def popup_menu():
        contents=next(w for w in descendants(popover) if w.get_css_name()=='contents')
        image=snapshot(contents,'menu')
        assert any(p[:3]==FAMILY['window'] for p in image.get_flattened_data()),'GTK4-POPUP: wrong menu surface'
        models=[w for w in descendants(popover) if w.get_css_name()=='modelbutton']
        (args.output/'menu-nodes.json').write_text(json.dumps([
            {'node':w.get_css_name(),'classes':list(w.get_css_classes()),'type':type(w).__name__}
            for w in descendants(popover)],indent=2)+'\n')
        assert models,'GTK4-POPUP: no model buttons'
        for model in models:model.set_state_flags(Gtk.StateFlags.PRELIGHT,False)
        GLib.timeout_add(100,guard(popup_labels));return False

    def popup_labels():
        labels=[w for w in descendants(popover) if isinstance(w,Gtk.Label) and w.get_label()]
        assert labels
        for label in labels:
            assert tuple(round(v*255) for v in color(label)[:3])==FAMILY['selection_foreground'],'GTK4-POPUP: model label'
        snapshot(popover,'menu-hover');report['popups'].append('menu')
        popover.popdown()
        dropdown.get_first_child().set_active(True)
        GLib.timeout_add(150,guard(dropdown_capture));return False

    def dropdown_capture():
        popup=next(w for w in descendants(dropdown) if isinstance(w,Gtk.Popover))
        assert popup.get_mapped(),'GTK4-POPUP: dropdown did not map'
        contents=next(w for w in descendants(popup) if w.get_css_name()=='contents')
        image=snapshot(contents,'dropdown')
        assert any(p[:3]==FAMILY['selection'] for p in image.get_flattened_data()),'GTK4-POPUP: dropdown selection'
        report['popups'].append('dropdown');popup.popdown()
        chooser_window=Gtk.Window(title='Private file chooser (no file opened)',transient_for=window)
        chooser=Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN)
        chooser.set_current_folder(Gio.File.new_for_path(os.environ['HOME']))
        chooser_window.set_child(chooser);chooser_window.set_default_size(900,600);chooser_window.present()
        def capture_chooser():
            assert chooser.get_mapped(),'GTK4-POPUP: chooser did not map'
            image=snapshot(chooser_window,'filechooser')
            assert any(p[:3]==FAMILY['window'] for p in image.get_flattened_data()),'GTK4-POPUP: chooser surface'
            report['popups'].append('filechooser');chooser_window.destroy();loop.quit();return False
        GLib.timeout_add(350,guard(capture_chooser));return False

    GLib.timeout_add(200,guard(apply_state));loop.run()
    window.destroy();renderer.unrealize()
    # Preserve partial evidence before propagating a failed assertion.
    (args.output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    if failures:raise failures[0]
    print(json.dumps(report))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme',type=Path,default=ROOT/'usr/share/themes/VGUI2Classic')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--state',choices=('normal','backdrop','rtl'),default='normal',help=argparse.SUPPRESS)
    parser.add_argument('--dark',action='store_true',help=argparse.SUPPRESS)
    parser.add_argument('--scale',type=int,default=1,choices=(1,2),help=argparse.SUPPRESS)
    parser.add_argument('--quick',action='store_true',help='one case for targeted negative controls')
    parser.add_argument('--strict',action='store_true',help='also reject reproduced Broadway timing warnings')
    args=parser.parse_args()
    if args.worker:worker(args);return
    theme=args.theme.resolve()
    assert (theme/'gtk-4.0/gtk.css').is_file() and (theme/'gtk-4.0/gtk-dark.css').is_file(),'GTK4-ENTRY: missing normal/dark entry'
    for path in (theme/'gtk-4.0').glob('*.css'):
        for url in re.findall(r'url\(["\']?([^"\')]+)',path.read_text()):
            assert (path.parent/url).is_file(),'GTK4-ASSET: '+url
    with tempfile.TemporaryDirectory(prefix='vgui2-gtk4-states-') as name:
        scratch=Path(name);env=os.environ.copy()
        for variable,folder in (('HOME','home'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),
                ('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state'),('XDG_RUNTIME_DIR','runtime')):
            path=scratch/folder;path.mkdir(mode=0o700);env[variable]=str(path)
        shutil.copytree(theme,scratch/'data/themes'/FAMILY['name'])
        staged_css=scratch/'data/themes'/FAMILY['name']/'gtk-4.0/gtk.css'
        staged_css.write_text(staged_css.read_text()+'\n@define-color vgui4_fixture_marker #11171d;\n')
        dark_css=staged_css.with_name('gtk-dark.css')
        dark_css.write_text(dark_css.read_text()+'\n@define-color vgui4_dark_fixture_marker #1d1711;\n')
        settings=scratch/'config/gtk-4.0';settings.mkdir()
        (settings/'settings.ini').write_text('[Settings]\ngtk-theme-name='+FAMILY['name']+'\ngtk-font-name=DejaVu Sans 10\n')
        env.update({'XDG_CONFIG_DIRS':str(scratch/'config'),'XDG_DATA_DIRS':'/usr/share',
                    'GDK_BACKEND':'broadway','BROADWAY_DISPLAY':':1','GSK_RENDERER':'broadway',
                    'GDK_DISABLE':'gl:vulkan:offload','VK_LOADER_DRIVERS_DISABLE':'*',
                    'GTK_A11Y':'none','GSETTINGS_BACKEND':'memory','GIO_USE_VFS':'local','GTK_USE_PORTAL':'0',
                    'GTK_MODULES':'','GTK_IM_MODULE':'gtk-im-context-simple','GDK_DPI_SCALE':'1','LC_ALL':'C.UTF-8'})
        for key in ('GTK_THEME','DISPLAY','WAYLAND_DISPLAY','GTK_PATH','GTK_DATA_PREFIX','GTK_DEBUG','GSK_DEBUG','GDK_DEBUG','DBUS_SESSION_BUS_ADDRESS'):env.pop(key,None)
        bus=scratch/'bus.conf'
        bus.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(scratch)+
                       '</listen><auth>EXTERNAL</auth><policy context="default"><allow own="*"/>'+
                       '<allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>')
        output=args.output.resolve() if args.output else scratch/'output';output.mkdir(parents=True,exist_ok=True)
        cases=[(args.state,args.dark,args.scale)] if args.quick else [('normal',False,1),('normal',True,1),('backdrop',False,1),('rtl',False,1),('normal',False,2)]
        reports=[]
        for state,dark,scale in cases:
            case=state+('-dark' if dark else '-normal')+'-'+str(scale)+'x'
            target=output/case;target.mkdir(parents=True,exist_ok=True);env['GDK_SCALE']=str(scale)
            env['GTK_THEME']=FAMILY['name']+(':dark' if dark else '')
            command=['dbus-run-session','--config-file='+str(bus),'--',sys.executable,'-I',str(Path(__file__).resolve()),
                     '--worker','--theme',str(theme),'--output',str(target),'--state',state,'--scale',str(scale)]
            if dark:command.append('--dark')
            # Fresh transport per worker: Broadway may retain render-node IDs
            # across disconnected applications and fail in its reuse cache.
            with private_display(scratch,env), FrameClient(scratch/'http.socket',scale) as client:
                result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=25)
                # Preserve worker diagnostics even if transport teardown fails.
                (target/'stdout').write_text(result.stdout);(target/'stderr').write_text(result.stderr)
            lines=[line for line in result.stderr.splitlines() if line.strip()]
            known=[line for line in lines if TIMING_WARNING.fullmatch(line)]
            unexpected=[line for line in lines if not TIMING_WARNING.fullmatch(line)]
            if result.returncode or unexpected or (args.strict and known):raise RuntimeError(result.stdout+result.stderr)
            assert client.frames>0,'Private GTK 4 display did not acknowledge frames'
            record=json.loads(result.stdout);record['acknowledged_frames']=client.frames;record['known_broadway_warnings']=known
            reports.append(record);print('VGUI2 GTK 4 states '+case+': PASS',flush=True)
        (output/'results.json').write_text(json.dumps(reports,indent=2)+'\n')


if __name__=='__main__':main()
