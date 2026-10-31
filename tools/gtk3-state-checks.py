"""Real-widget selection and message contrast checks for the classic family."""
import json


def build(Gtk, body):
    grid = Gtk.Grid(column_spacing=16, row_spacing=6)
    body.pack_start(grid, True, True, 0)
    samples = []
    inactive = []
    for column, backdrop in enumerate((False, True)):
        grid.attach(Gtk.Label(label='Inactive' if backdrop else 'Active'), column, 0, 1, 1)
        for row, kind in enumerate(('info', 'warning', 'error', 'question',
                                    'list', 'flow', 'disabled-list', 'disabled-flow'), 1):
            label = Gtk.Label(label=kind+' message / selection', margin=8, xalign=0)
            if row <= 4:
                container = Gtk.InfoBar(message_type=getattr(Gtk.MessageType, kind.upper()))
                container.get_content_area().add(label)
                samples.append((kind, backdrop, False, label))
            else:
                box = Gtk.Box(spacing=12)
                box.pack_start(label, True, True, 0)
                button = Gtk.Button(label='Nested button')
                box.pack_start(button, False, False, 8)
                disabled = kind.startswith('disabled-')
                if kind.endswith('list'):
                    container = Gtk.ListBox()
                    container.add(box)
                    selected = container.get_row_at_index(0)
                    container.select_row(selected)
                else:
                    container = Gtk.FlowBox()
                    container.set_selection_mode(Gtk.SelectionMode.SINGLE)
                    container.set_max_children_per_line(1)
                    container.add(box)
                    selected = container.get_child_at_index(0)
                    container.select_child(selected)
                selected.set_sensitive(not disabled)
                samples.extend(((kind, backdrop, disabled, label),
                                (kind+'-button', backdrop, disabled, button.get_child())))
            grid.attach(container, column, row, 1, 1)
            if backdrop:
                inactive.append(container)

    def apply():
        def recurse(widget):
            widget.set_state_flags(Gtk.StateFlags.BACKDROP, False)
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    recurse(child)
        for widget in inactive:
            recurse(widget)
        return False

    def verify(window, image, output):
        def luminance(rgb):
            return sum(w*(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4)
                       for w,v in zip((.2126,.7152,.0722), rgb))
        reports = []
        failures = []
        for kind, backdrop, disabled, label in samples:
            flags = label.get_state_flags()
            assert bool(flags & Gtk.StateFlags.BACKDROP) == backdrop
            assert bool(flags & Gtk.StateFlags.INSENSITIVE) == disabled
            fg = label.get_style_context().get_color(flags)
            # Sample the actual parent/button fill just outside the label;
            # the explicit margins/padding keep this away from glyphs/edges.
            point = label.translate_coordinates(window, -2, label.get_allocated_height()//2)
            pixel = image.getpixel(point)
            assert pixel[3] == 255, (kind, point, pixel)
            bg = [v/255 for v in pixel[:3]]
            text = [v*fg.alpha+b*(1-fg.alpha) for v,b in zip((fg.red,fg.green,fg.blue),bg)]
            a,b = sorted((luminance(text),luminance(bg)))
            ratio = (b+.05)/(a+.05)
            passed = fg.alpha < 1 if disabled else ratio >= 4.5
            report = {'kind':kind, 'backdrop':backdrop, 'disabled':disabled,
                      'foreground':[round(v,5) for v in (fg.red,fg.green,fg.blue,fg.alpha)],
                      'painted_background':list(pixel), 'contrast':round(ratio,3), 'passed':passed}
            reports.append(report)
            if not passed:
                failures.append(report)
        (output/'states-details.json').write_text(json.dumps(reports,indent=2)+'\n')
        assert not failures, 'GTK3-STATES: '+json.dumps(failures)
        return reports
    return apply, verify
