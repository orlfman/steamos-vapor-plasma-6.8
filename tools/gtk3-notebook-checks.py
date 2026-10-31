"""Inspect overflow-arrow styles on mapped notebooks in both directions."""
import json
import re
import hashlib


def build(Gtk, body):
    import cairo
    grid=Gtk.Grid(column_spacing=12,row_spacing=12)
    body.pack_start(grid,True,True,0)
    notebooks=[]
    for row,position in enumerate(('top','bottom','left','right')):
        for column,direction in enumerate(('ltr','rtl')):
            notebook=Gtk.Notebook(scrollable=True)
            notebook.set_tab_pos(getattr(Gtk.PositionType,position.upper()))
            notebook.set_direction(getattr(Gtk.TextDirection,direction.upper()))
            notebook.set_size_request(350,180)
            for i in range(18):
                notebook.append_page(Gtk.Label(label='Page content'),Gtk.Label(label='Page '+str(i+1)))
            grid.attach(notebook,column,row,1,1)
            notebooks.append((position,direction,notebook))

    def verify(_window,_image,output):
        reports=[]
        failures=[]
        for position,direction,notebook in notebooks:
            style=notebook.get_style_context().to_string(
                Gtk.StyleContextPrintFlags.RECURSE|Gtk.StyleContextPrintFlags.SHOW_STYLE)
            (output/('notebook-'+position+'-'+direction+'.txt')).write_text(style)
            assert 'header.'+position in style,(position,style)
            arrows={}
            expected={'down':'pan-up-symbolic','up':'pan-down-symbolic'} if position in ('left','right') else {
                'down':'pan-start-symbolic','up':'pan-end-symbolic'}
            for name,icon in expected.items():
                # Public GTK does not expose internal arrow contexts. Confirm
                # the live nodes, then render their documented paths with GTK's
                # named theme provider and compare to the correct symbolic icon.
                match=re.search(r'(?m)^\s*arrow\.'+name+r'([^\n]*)',style)
                assert match,(position,name,style)
                flags=Gtk.StateFlags.DIR_RTL if direction=='rtl' else Gtk.StateFlags.DIR_LTR
                if ':disabled' in match.group(1):flags |= Gtk.StateFlags.INSENSITIVE
                path=Gtk.WidgetPath.new();parent=None
                for index,(node,classes) in enumerate((('notebook',('frame',)),('header',(position,)),('tabs',()),('arrow',(name,)))):
                    path.append_type(Gtk.Notebook if index==0 else Gtk.Widget)
                    path.iter_set_object_name(index,node);path.iter_set_state(index,flags)
                    for cls in classes:path.iter_add_class(index,cls)
                    context=Gtk.StyleContext.new();context.set_path(path);context.set_state(flags)
                    if parent:context.set_parent(parent)
                    context.add_provider(Gtk.CssProvider.get_named('VGUI2Classic',None),Gtk.STYLE_PROVIDER_PRIORITY_THEME)
                    parent=context
                def paint():
                    surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,20,20)
                    Gtk.render_check(context,cairo.Context(surface),0,0,20,20)
                    surface.flush()
                    return bytes(surface.get_data())
                actual=paint()
                reference=Gtk.CssProvider()
                reference.load_from_data(('arrow { -gtk-icon-source: -gtk-icontheme("'+icon+'"); }').encode())
                context.add_provider(reference,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
                correct=paint()
                assert any(actual) and any(correct),(position,direction,name,'blank icon')
                arrows[name]={'expected_icon':icon,'passed':actual==correct,
                              'actual_sha256':hashlib.sha256(actual).hexdigest(),
                              'reference_sha256':hashlib.sha256(correct).hexdigest()}
            passed=all(arrow['passed'] for arrow in arrows.values())
            report={'position':position,'direction':direction,'arrows':arrows,'passed':passed}
            reports.append(report)
            if not passed:failures.append(report)
        (output/'notebooks-details.json').write_text(json.dumps(reports,indent=2)+'\n')
        assert not failures,'GTK3-NOTEBOOK: '+json.dumps(failures)
        return reports
    return verify
