"""Additional real-widget coverage found necessary by the GTK 4 port audit."""
import json


def build(Gtk, body):
    fixtures=Gtk.Box(spacing=12)
    body.append(fixtures)
    frames=[]
    for name,widget in (
            ('frame',Gtk.Frame(child=Gtk.Label(label='Framed content'))),
            ('scrolled-frame',Gtk.ScrolledWindow(has_frame=True,child=Gtk.Label(label='Framed scroll'))),
            ('scrolled-plain',Gtk.ScrolledWindow(has_frame=False,child=Gtk.Label(label='Plain scroll')))):
        widget.set_size_request(140,60);fixtures.append(widget);frames.append((name,widget))
    fields=[]
    for name,orientation in (('horizontal',Gtk.Orientation.HORIZONTAL),('vertical',Gtk.Orientation.VERTICAL),('vertical-disabled',Gtk.Orientation.VERTICAL)):
        spin=Gtk.SpinButton.new_with_range(0,100,1)
        spin.set_orientation(orientation);spin.set_value(50)
        spin.set_sensitive(name!='vertical-disabled')
        fixtures.append(spin);fields.append((name,spin))
    selections=Gtk.Box(spacing=12)
    body.append(selections)
    label=Gtk.Label(label='MMMMMMMM',selectable=True)
    entry=Gtk.Entry(text='MMMMMMMM')
    view=Gtk.TextView();view.get_buffer().set_text('MMMMMMMM')
    selected=[('label',label,(77,88,69)),('entry',entry,(63,70,56)),('textview',view,(63,70,56))]
    for _name,widget,_background in selected:
        widget.set_size_request(160,36);selections.append(widget)
    tables=Gtk.Box(spacing=12);body.append(tables)
    columns=[]
    for separators in (False,True):
        model=Gtk.NoSelection.new(Gtk.StringList.new(['First','Second']))
        table=Gtk.ColumnView(model=model,show_column_separators=separators,show_row_separators=separators)
        for title in ('Name','Value'):
            factory=Gtk.SignalListItemFactory()
            factory.connect('setup',lambda _f,item:item.set_child(Gtk.Label(label='Cell',xalign=0)))
            table.append_column(Gtk.ColumnViewColumn(title=title,factory=factory))
        tables.append(table);columns.append((separators,table))
    expanders=[]
    for expanded in (False,True):
        pair=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        widgets=[]
        for _ in range(2):
            expander=Gtk.Expander(label='Expanded' if expanded else 'Collapsed',expanded=expanded,child=Gtk.Label(label='Details'))
            pair.append(expander);widgets.append(expander)
        tables.append(pair);expanders.append((expanded,*widgets))

    def descendants(widget):
        child=widget.get_first_child()
        while child:
            yield child;yield from descendants(child);child=child.get_next_sibling()

    def arrow_for(widget):return next(w for w in descendants(widget) if w.get_css_name()=='expander')

    def apply_controls():
        # Apply to actual title widgets once, before the first capture. Paired
        # references avoid repeatedly forcing focus on the expander container.
        for _expanded,base,focused in expanders:
            arrow_for(base).get_parent().unset_state_flags(Gtk.StateFlags.FOCUSED|Gtk.StateFlags.FOCUS_VISIBLE)
            arrow_for(focused).get_parent().set_state_flags(Gtk.StateFlags.FOCUSED|Gtk.StateFlags.FOCUS_VISIBLE,False)

    def select_view():
        buffer=view.get_buffer();buffer.select_range(buffer.get_start_iter(),buffer.get_end_iter())
    select_functions=(lambda:label.select_region(0,-1),lambda:entry.select_region(0,-1),select_view)

    def verify(window,image,snapshot,symbolic_image,style_focus,scale,output):
        reports=[]
        for name,widget in frames:
            border=widget.get_style_context().get_border()
            capture=snapshot(widget,'audit-'+name)
            pixel=capture.getpixel((capture.width//2,0))
            widths=[border.top,border.right,border.bottom,border.left]
            expected=0 if name=='scrolled-plain' else 1
            # Cairo antialiases the outside edge of GTK 4's one-pixel frame.
            passed=widths==[expected]*4 and (expected==0 or (pixel[:3]==(122,135,108) and pixel[3]>=245))
            reports.append({'name':name,'borders':widths,'top_pixel':list(pixel),'passed':passed})
        for name,spin in fields:
            text=spin.get_first_child()
            while text and text.get_css_name()!='text':text=text.get_next_sibling()
            assert text is not None
            ok,bounds=text.compute_bounds(window);assert ok
            point=(round(bounds.get_x()+bounds.get_width()/2)*scale,round(bounds.get_y()+3)*scale)
            pixel=image.getpixel(point)
            foreground=text.get_color()
            reports.append({'name':name+'-spin-field','painted_background':list(pixel),
                            'foreground_alpha':round(foreground.alpha,5),
                            'passed':pixel==(63,70,56,255) and (name!='vertical-disabled' or foreground.alpha<1)})
        for separators,table in columns:
            cells=[w for w in descendants(table) if w.get_css_name()=='cell']
            assert len(cells)==4
            borders=[];passed=True
            for index,cell in enumerate(cells):
                border=cell.get_style_context().get_border()
                side=border.left if table.get_direction()==Gtk.TextDirection.RTL else border.right
                expected=int(separators and index%2==0)
                passed &= side==expected
                borders.append([border.top,border.right,border.bottom,border.left])
            rows=[w for w in descendants(table) if w.get_css_name()=='row']
            row_padding=[w.get_style_context().get_padding() for w in rows]
            padding=[[p.top,p.right,p.bottom,p.left] for p in row_padding]
            passed &= all(p==[0,0,0,0] for p in padding)
            row_borders=[w.get_style_context().get_border().bottom for w in rows]
            passed &= row_borders==([1,0] if separators else [0,0])
            reports.append({'name':'column-separators-'+str(separators),'cell_borders':borders,
                            'row_padding':padding,'row_bottom_borders':row_borders,'passed':bool(passed)})
        for expanded,expander,focused in expanders:
            arrow=arrow_for(expander)
            size=[arrow.get_width(),arrow.get_height()]
            overlap=0
            if min(size)>=16:
                try:actual=snapshot(arrow,'expander-'+str(expanded))
                except AssertionError as error:
                    if error.args==(('expander-'+str(expanded),'empty snapshot'),):actual=None
                    else:raise
                expected=symbolic_image(arrow,'pan-down-symbolic' if expanded else 'pan-end-symbolic','expander-'+str(expanded))
                if actual is not None:
                    # The padded title can allocate extra vertical space to
                    # its icon widget; compare the centered 16px glyph itself.
                    side=16*scale;x=(actual.width-side)//2;y=(actual.height-side)//2
                    actual=actual.crop((x,y,x+side,y+side))
                def support(image):
                    alpha=list(image.getchannel('A').get_flattened_data())
                    if not max(alpha):return set()
                    result=set();width=16*scale;peak=max(alpha)
                    for y in range(16):
                        for x in range(16):
                            value=sum(alpha[(y*scale+dy)*width+x*scale+dx]/peak for dy in range(scale) for dx in range(scale))/scale**2
                            if value>.2:result.add(y*16+x)
                    return result
                a=support(actual) if actual is not None else set();b=support(expected)
                if a|b:overlap=len(a&b)/len(a|b)
            reports.append({'name':'expander-'+str(expanded),'arrow_size':size,'glyph_support_iou':round(overlap,5),'passed':overlap>=.85})
            title=arrow.get_parent()
            ratio=style_focus(arrow_for(focused).get_parent(),title,'expander-title-'+str(expanded))
            reports.append({'name':'expander-focus-'+str(expanded),'contrast':round(ratio,3),
                            'method':'Paired native title widgets with synthetic focus state','passed':ratio>=3})
        (output/'audit-controls.json').write_text(json.dumps(reports,indent=2)+'\n')
        assert all(item['passed'] for item in reports),'GTK4-CONTROLS: '+json.dumps(reports)
        return reports

    def check_selection(name,widget,under,window,image,scale):
        inactive=bool(widget.get_state_flags() & Gtk.StateFlags.BACKDROP)
        expected_bg=tuple(round((v+b)/2) for v,b in zip((149,136,49),under)) if inactive else (149,136,49)
        expected_fg=(252,252,252) if inactive else (24,24,16)
        ok,bounds=widget.compute_bounds(window);assert ok
        region=image.crop((round(bounds.get_x())*scale,round(bounds.get_y())*scale,
                           round(bounds.get_x()+bounds.get_width())*scale,round(bounds.get_y()+bounds.get_height())*scale))
        pixels=list(region.get_flattened_data())
        fills=sum(p[3]==255 and max(abs(v-b) for v,b in zip(p[:3],expected_bg))<=1 for p in pixels)
        # Thick M strokes contain solid ink. Requiring multiple columns
        # prevents a lone caret from satisfying the foreground assertion.
        ink_columns={i%region.width for i,p in enumerate(pixels) if p[3]==255 and p[:3]==expected_fg}
        report={'name':name+'-selection','backdrop':inactive,'expected_fill':list(expected_bg),
                        'fill_pixels':fills,'expected_ink':list(expected_fg),'ink_columns':len(ink_columns),
                        'passed':fills>20*scale and len(ink_columns)>3*scale}
        assert report['passed'],'GTK4-TEXT-SELECTION: '+json.dumps(report)
        return report
    steps=[]
    for (name,widget,under),apply in zip(selected,select_functions):
        def check(window,image,scale,name=name,widget=widget,under=under):
            return check_selection(name,widget,under,window,image,scale)
        steps.append((name,apply,check))
    return verify,steps,apply_controls
