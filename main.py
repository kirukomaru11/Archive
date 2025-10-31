#!/usr/bin/python3
import gi, os, shutil, marshal, zipfile
for a, b in (("Gtk", "4.0"), ("Adw", "1"), ("Gly", "2"), ("GlyGtk4", "2"), ("AppStream", "1.0")): gi.require_version(a, b)
from gi.repository import AppStream, Gio, GLib, Gtk, Adw, Gdk, Gly, GlyGtk4
from MasonryBox import MasonryBox
from PaintableColorThief import palette
from TagRow import TagRow
com = (m := AppStream.Metadata(), m.parse_file(Gio.File.new_for_path(os.path.join(GLib.get_system_data_dirs()[0], "metainfo", "io.github.kirukomaru11.Archive.metainfo.xml")), 1), m.get_component())[-1]
Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_search_path(os.path.join(GLib.get_system_data_dirs()[0], com.props.id))
(s := Gtk.CssProvider.new(), s.load_from_path(os.path.join(GLib.get_system_data_dirs()[0], com.props.id, "style.css")), Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), s, 800))
app = Adw.Application(application_id=com.props.id)
app.register()
(app.run(), exit()) if app.props.is_remote else None
app.modifying = False
file_launcher, uri_launcher = Gtk.FileLauncher.new(), Gtk.UriLauncher.new()
Action = lambda n, s, c: (a := Gio.SimpleAction.new(n, None), app.add_action(a), app.set_accels_for_action(f"app.{n}", s), a.connect("activate", c))
shortcuts, about = Adw.ShortcutsDialog(), Adw.AboutDialog(application_icon=f"{com.props.id}-symbolic", application_name=com.props.name, developer_name=com.get_developer().get_name(), issue_url=tuple(com.props.urls.values())[0], website=tuple(com.props.urls.values())[-1], license_type=7, version=com.get_releases_plain().get_entries()[0].get_version(), release_notes=com.get_releases_plain().get_entries()[0].get_description())
Action("about", (), lambda *_: about.present(app.props.active_window))
Action("shortcuts", ("<primary>question",), lambda *_: shortcuts.present(app.props.active_window))
section = Adw.ShortcutsSection(title="General")
for t, a in (("Keyboard Shortcuts", "<primary>question"), ("Toggle Hidden", "<primary>h"), ("Search", "<primary>f"), ("Sidebar", "F9"), ("Fullscreen", "F11"), ("Open Current Folder", "<primary>o"), ("Paste Image/File/Folder", "<primary>v")): section.add(Adw.ShortcutsItem(title=t, accelerator=a))
shortcuts.add(section)
def Button(t="button", callback=None, icon_name="", bindings=(), **kargs):
    bt = Gtk.MenuButton if t == "menu" else Gtk.ToggleButton if t == "toggle" else Gtk.Button
    bt = bt(icon_name=icon_name + "-symbolic" if icon_name else "", **kargs)
    if callback: bt.connect("clicked" if t == "button" else "notify::active", callback)
    for b in bindings:
        source = b[0] if b[0] else bt
        source.bind_property(b[1], b[2] if b[2] else bt, b[3], b[4] if len(b) >= 5 and b[4] else 0 | 2, b[5] if len(b) >= 6 else None)
    return bt
def set_colors(file):
    if not app.props.active_window: return
    if hasattr(file, "colors") and app.lookup_action("colors").props.state:
        style = Gtk.CssProvider()
        GLib.idle_add(style.load_from_string, ":root {" + "".join(tuple(f"--color-{i + 1}: rgb{color};" for i, color in enumerate(file.colors))) + "}")
        GLib.idle_add(Gtk.StyleContext.add_provider_for_display, *(app.props.active_window.props.display, style, 700))
        GLib.idle_add(app.props.active_window.add_css_class, "colored")
    else:
        GLib.idle_add(app.props.active_window.remove_css_class, "colored")
def set_file(file):
    app.modifying = True
    app.file = file
    delete_dialog.props.heading = f"Delete {app.file.get_basename() if app.file else ''}"
    file_launcher.props.file = app.file
    edit.props.title = app.file.get_basename() if app.file else ""
    cover_button.props.visible = False
    if file.parent.has_parent(app_data):
        cover_button.props.title = "Erase Cover" if tuple(i for i in app.all_files if i.has_parent(app_data) and i.get_basename() == app_data.get_relative_path(app.file).replace(GLib.DIR_SEPARATOR_S, " @ ")) else "Select Cover"
        cover_button.props.visible = True
    for r, i, p in properties[1:]:
        r.props.visible = r.props.name in app.data[0][app_data.get_relative_path(app.file)] if app_data.get_relative_path(app.file) in app.data[0] else False
        if r.props.visible:
            s = app.data[0][app_data.get_relative_path(app.file)][r.props.name] if r.props.name in app.data[0][app_data.get_relative_path(app.file)] else s
            if isinstance(s, int) and isinstance(i, Gtk.Calendar):
                s = GLib.DateTime.new_from_unix_utc(s)
            setattr(i.props, i.p, s)
    path.props.text = app.file.get_basename() if app.file else ""
    if not notes_row.props.visible:
        edit.props.visible_page = edit_page
    GLib.idle_add(set_colors, app.file)
    app.modifying = False
def entry_video(widget):
    m = Gtk.MediaFile.new_for_file(widget.display)
    m.bind_property("playing", m, "volume", 0 | 2, lambda b, v: 0)
    m.props.loop = m.props.playing = True
    widget.props.child.props.paintable = m
def load_picture(task, widget, d, c):
    cover = tuple(i for i in app.all_files if i.has_parent(app_data) and i.get_basename() == app_data.get_relative_path(widget.file).replace(GLib.DIR_SEPARATOR_S, " @ "))
    widget.display = cover[0] if cover else widget.file
    if not cover and os.path.isdir(widget.file.peek_path()):
        widget.display = tuple(i for i in app.all_files if i.has_parent(widget.file))[0]
    if cover or Gio.content_type_guess(widget.display.get_basename())[0].startswith("image"):
        image = Gly.Loader.new(widget.display).load()
    elif widget.display.get_basename().endswith("cbz"):
        i = sorted((i for i in zipfile.ZipFile(widget.display.peek_path(), "r").namelist() if Gio.content_type_guess(i)[0].startswith("image")), key=lambda i: GLib.utf8_collate_key_for_filename(i, -1))
        image = Gly.Loader.new_for_bytes(GLib.Bytes.new(zipfile.ZipFile(widget.display.peek_path(), "r").read(i[0]))).load()
    else: return entry_video(widget)
    widget.height = image.get_height() / image.get_width()
    frame = image.next_frame()
    t = GlyGtk4.frame_get_texture(frame)
    widget.file.colors = palette(t)
    if frame.get_delay() > 0: return entry_video(widget)
    widget.props.child.props.paintable = t
def do_search(*_):
    if app.modifying: return
    catalog.page, catalog.end = 0, False
    catalog.remove_all()
    for i in overlays: i.set_visible(False)
    app.file = sidebar.props.selected_item.file if sidebar.props.selected_item else None
    if not app.file: return overlays[0].set_visible(True)
    files = tuple(i for i in app.all_files if i.has_parent(app.file))
    if not files: return overlays[0].set_visible(True)
    catalog.c, t, s = [], search_layout.get_child("search").props.text.lower(), search_layout.get_child("status").props.active
    for f in files:
        o = app.data[0][app_data.get_relative_path(f)]
        if o["hidden"] and not app.lookup_action("hidden").props.state: continue
        elif t and not t in f"{f.get_basename()} {o['notes']} {o['tags']} {o['target']}".lower(): continue
        elif not s == 0 and not s - 1 == o["status"]: continue
        catalog.c.append(f)
    if not catalog.c: return overlays[1].set_visible(True)
    s, k = app.lookup_action("sort").props.state.get_string().strip("'"), lambda c: GLib.random_int()
    if "Alphabetical" in s:
        k = lambda e: GLib.utf8_collate_key_for_filename(e.peek_path(), -1)
    elif "Launched" in s:
        k = lambda e: app.data[0][app_data.get_relative_path(e)]["launched"]
    elif "Date" in s:
        k = lambda e: app.data[0][app_data.get_relative_path(e)]["date"]
    catalog.c.sort(key=k, reverse="Descending" in s)
    catalog_load_more(catalog.props.child, 3)
def catalog_load_more(sw, p):
    m = sw.props.parent
    if p == 3 and not m.end:
        m.end = True
        m.page += 1
        pages = tuple(m.c[i:i + 30] for i in range(0, len(m.c), 30))
        if not m.page > len(pages):
            for file in pages[m.page - 1]:
                if file.peek_path() in m.h:
                    entry = m.h[file.peek_path()]
                else:
                    entry = Gtk.Overlay(child=Gtk.Picture())
                    entry.props.child.props.paintable = Adw.SpinnerPaintable.new(entry.props.child)
                    entry.file = file
                    Gio.Task.new(entry).run_in_thread(load_picture)
                    event = Gtk.EventControllerMotion()
                    event.connect("enter", lambda e, x, y: GLib.idle_add(set_colors, e.props.widget.file))
                    entry.add_overlay(Gtk.Revealer(child=Button(css_classes=("osd", "circular"), tooltip_text="More", icon_name="view-more", callback=lambda b: (set_file(b.get_ancestor(Gtk.Overlay).file), edit.present(app.props.active_window))), transition_type=1, halign=2, valign=1))
                    event.bind_property("contains-pointer", entry.get_last_child(), "reveal-child", 0 | 2)
                    entry.add_controller(event)
                    m.h[file.peek_path()] = entry
                GLib.idle_add(m.add, entry)
            m.end = False
def load_f_catalog(file):
    f_catalog.file, f_catalog.page, f_catalog.end = file, 0, False
    f_catalog.c = tuple(i for i in app.all_files if i.has_parent(f_catalog.file))
    f_catalog.remove_all()
    catalog_load_more(f_catalog.props.child, 3)
def catalog_activate(m, c, b):
    set_file(c.file if c.file.parent.has_parent(app_data) else f_catalog.file)
    if app.data[0][app_data.get_relative_path(app.file)]["target"] and app.lookup_action("launch-targets").props.state:
        if app.data[0][app_data.get_relative_path(app.file)]["target"].startswith("https://"):
            uri_launcher.set_uri(app.data[0][app_data.get_relative_path(app.file)]["target"])
            uri_launcher.launch()
        else: Gio.AppInfo.create_from_commandline(f"flatpak-spawn --host {app.data[0][app_data.get_relative_path(app.file)]['target']}", None, 0).launch()
    else:
        if c.file.query_file_type(0) == 2:
            load_f_catalog(c.file)
            navigation_view.find_page("f").props.title = c.file.get_basename()
            navigation_view.push_by_tag("f")
            return
        file_launcher.set_file(c.file)
        file_launcher.launch()
    toast_overlay.add_toast(Adw.Toast(title=f"{c.file.get_basename()} launched!"))
    app.data[0][app_data.get_relative_path(app.file)]["launched"] = GLib.DateTime.new_now_utc().to_unix()
    if app.lookup_action("exit-launch").props.state: app.props.active_window.close()
catalog, f_catalog = tuple(MasonryBox(activate=catalog_activate) for _ in range(2))
for i in (catalog, f_catalog):
    i.h = {}
    i.props.child.connect("edge-reached", catalog_load_more)

navigation_view, overlay = Adw.NavigationView(), Gtk.Overlay(child=catalog)
for t, i in (("Add an Entry", "document-new"), ("No Results", "edit-find")): overlay.add_overlay(Adw.StatusPage(icon_name=i + "-symbolic", title=t, visible=False))
overlays = tuple(i for i in overlay if isinstance(i, Adw.StatusPage))
search_layout = Adw.MultiLayoutView()
search_layout.set_child("search", Gtk.SearchEntry(placeholder_text="Search", hexpand=True))
search_layout.get_child("search").connect("stop-search", lambda *_: search_bar.set_search_mode(False))
search_layout.get_child("search").connect("search-changed", do_search)
search_layout.set_child("status", Adw.ToggleGroup())
statuses = (("All", "view-grid"), ("In Progress", "folder-recent"), ("Finished", "selection-mode"), ("Planned", "month"))
for t, i in statuses: search_layout.get_child("status").add(Adw.Toggle(icon_name=i + "-symbolic", tooltip=t))   
search_layout.get_child("status").connect("notify::active", do_search)
search_layout.add_layout(Adw.Layout(content=Gtk.CenterBox(hexpand=True, center_widget=Adw.Clamp(child=Adw.LayoutSlot.new("search"), maximum_size=300), end_widget=Adw.LayoutSlot.new("status")), name="wide"))
narrow = Gtk.Box(orientation=1, hexpand=True)
narrow.append(Adw.Clamp(child=Adw.LayoutSlot.new("search"), maximum_size=268))
narrow.append(Adw.Bin(child=Adw.LayoutSlot.new("status"), halign=3))
search_layout.add_layout(Adw.Layout(content=narrow, name="narrow"))
toolbar, header = Adw.ToolbarView(content=overlay), Adw.HeaderBar()

add_menu = Gio.Menu.new()
for t, a in (("Add File", "add-file"), ("Add Folder", "add-folder")): add_menu.append(t, "app." + a)
add_menu.freeze()
menus = tuple(Gio.Menu.new() for _ in range(6))
sorts = ("Random", "Alphabetical Ascending", "Alphabetical Descending", "Launched Ascending", "Launched Descending", "Date Ascending", "Date Descending")
for i in sorts: menus[4].append(i, f"app.sort::{i}")
menus[4].name = "Sort"
for n, i in enumerate(((("Fullscreen", "fullscreen"), ("Open Current Folder", "open-folder"),),
                    menus[4],
                    (("Show Hidden", "hidden"), ("Launch Targets", "launch-targets"), ("Exit After Launch", "exit-launch"), ("Cover Color Theming", "colors"), ("Clear Unused", "clear-unused")),
                    (("Keyboard Shortcuts", "shortcuts"), (f"About {about.props.application_name}", "about")),)):
    if isinstance(i, Gio.Menu):
        menus[n].append_submenu(i.name, i)
    else:
        for t, a in i: menus[n].append(t, "app." + a)
for i in menus[:4]: (i.freeze(), menus[5].append_section(None, i))
menus[5].freeze()

Action("fullscreen", ("F11",), lambda *_: toolbar.set_reveal_top_bars(not toolbar.props.reveal_top_bars))
search_bar = Gtk.SearchBar(child=search_layout)
search_bar.connect_entry(search_layout.get_child("search"))
Action("search", ("<primary>f",), lambda *_: search_bar.set_search_mode(not search_bar.props.search_mode_enabled))
for i in (header, search_bar): toolbar.add_top_bar(i)
for i in (Button(t="menu", icon_name="open-menu", tooltip_text="Menu", menu_model=menus[5]), Button(t="toggle", icon_name="edit-find", tooltip_text="Search", bindings=((None, "active", search_bar, "search-mode-enabled", 0 | 1 | 2),))): header.pack_end(i)

free_filter, no_h_filter = tuple(Gtk.BoolFilter.new(Gtk.ClosureExpression.new(bool, i)) for i in (lambda i: True, lambda i: not app.data[0][app_data.get_relative_path(i.file)]["hidden"]))
sidebar, s_section = Adw.Sidebar(drop_preload=True, placeholder=Adw.StatusPage(icon_name="tag-outline-add-symbolic", title="Add a Category")), Adw.SidebarSection()
def drop(s, i, v, a):
    if v[0] in app.all_files:
        a, b = app_data.get_relative_path(sidebar.get_item(i).file), app_data.get_relative_path(v[0])
        app.data[0][a]["id"], app.data[0][b]["id"] = app.data[0][b]["id"], app.data[0][a]["id"]
        GLib.idle_add(sidebar_section)
        return True
def add_drag(w):
    b = w.get_ancestor(Gtk.ListBoxRow).props.child
    if hasattr(b, "dr") or not w.get_mapped(): return
    b.props.name = w.f.get_basename()
    b.dr = Gtk.DragSource(actions=Gdk.DragAction.COPY, content=Gdk.ContentProvider.new_for_value(Gdk.FileList.new_from_list((w.f,))))
    b.dr.connect("drag-begin", lambda e, d: Gtk.DragIcon.get_for_drag(d).set_child(Gtk.Label(margin_top=10, margin_start=10, label=e.props.widget.props.name, css_classes=["title-4"])))
    b.add_controller(b.dr)
def sidebar_section():
    if app.modifying: return
    app.modifying = True
    s_section.remove_all()
    for i in sorted((i for i in app.all_files if i.has_parent(app_data) and os.path.isdir(i.peek_path())), key=lambda a: app.data[0][app_data.get_relative_path(a)]["id"]):
        if tuple(it for it in sidebar.props.items if it.file == i): continue
        a = Adw.SidebarItem(title=i.get_basename(), drag_motion_activate=False, suffix=Adw.Bin())
        a.file = i
        a.props.suffix.f = i
        a.props.suffix.connect("map", add_drag)
        s_section.append(a)
    GLib.idle_add(sidebar.set_selected, 0)
    app.modifying = False
sidebar.connect("drop", drop)
sidebar.setup_drop_target(Gdk.DragAction.COPY, (Gdk.FileList,))
sidebar.append(s_section)
sidebar.connect("notify::selected", do_search)
sidebar_toolbar, sidebar_header = Adw.ToolbarView(content=sidebar), Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Categories"))
def new_category_response(d, r):
    if not r == "confirm" or not new_category.props.extra_child.props.text: return
    f, n = app_data.get_child(new_category.props.extra_child.props.text), 1
    while os.path.exists(f.peek_path()):
        n += 1
        f = app_data.get_child(f"{new_category.props.extra_child.props.text} {n}")
    f.make_directory()
new_category = Adw.AlertDialog(heading="New Category", css_classes=["alert", "floating", "new-dialog"], extra_child=Gtk.Entry(), default_response="cancel")
key = Gtk.EventControllerKey()
key.connect("key-pressed", lambda e, kv, *_: (e.props.widget.get_ancestor(Adw.Dialog).close(), True)[-1] if kv == 65307 else False)
new_category.props.extra_child.add_controller(key)
new_category.connect("response", new_category_response)
new_category.props.extra_child.connect("activate", lambda e: e.get_ancestor(Adw.Dialog).do_response("confirm"))
for i in ("cancel", "confirm"): new_category.add_response(i, i.title())
new_category.set_response_appearance("confirm", 1)
sidebar_header.pack_start(Button(tooltip_text="New Category",icon_name="tag-outline-add-symbolic", callback=lambda *_: new_category.present(app.props.active_window)))
sidebar_header.pack_end(Button(tooltip_text="Edit", icon_name="document-edit", callback=lambda *_: (set_file(sidebar.props.selected_item.file if sidebar.props.selected_item else None), edit.present(app.props.active_window) if app.file else None)))
sidebar_toolbar.add_top_bar(sidebar_header)
split_view = Adw.OverlaySplitView(content=toolbar, sidebar=sidebar_toolbar, pin_sidebar=True)
search_bar.props.key_capture_widget = split_view
Action("sidebar", ("F9",), lambda *_: split_view.set_show_sidebar(not split_view.props.show_sidebar))
for i in ((Button(t="menu", icon_name="list-add", tooltip_text="Add", menu_model=add_menu)), Button(t="toggle", icon_name="sidebar-show", tooltip_text="Sidebar", bindings=((None, "active", split_view, "show-sidebar", 0 | 1 | 2),))): header.pack_start(i)
navigation_view.add(Adw.NavigationPage(child=split_view, tag="c"))
sidebar.bind_property("selected-item", navigation_view.find_page("c"), "title", 0 | 2, lambda b, v: v.props.title if v else about.props.application_name)

f_toolbar, f_header = Adw.ToolbarView(content=f_catalog), Adw.HeaderBar()
for i in (sidebar_toolbar, f_toolbar): toolbar.bind_property("reveal-top-bars", i, "reveal-top-bars", 0)
f_header.pack_end(Button(t="menu", icon_name="open-menu", tooltip_text="Menu", menu_model=menus[5]))
f_header.pack_start(Button(icon_name="list-add", tooltip_text="Add", action_name="app.add-file"))
f_toolbar.add_top_bar(f_header)
navigation_view.add(Adw.NavigationPage(child=f_toolbar, tag="f"))

toast_overlay = Adw.ToastOverlay(child=navigation_view)
controller_key, t_drop = Gtk.EventControllerKey(), Gtk.DropTarget(preload=True, actions=1, formats=Gdk.ContentFormats.parse("GdkTexture GdkFileList"))
def add(v):
    if not sidebar.props.selected_item:
        app_data.get_child("New Category").make_directory()
        sidebar.props.selected = 0
    m = f_catalog.file if f_catalog.get_mapped() else sidebar.props.selected_item.file
    if isinstance(v, Gdk.Texture): v.save_to_png(m.peek_path() + GLib.DIR_SEPARATOR_S + f"{GLib.DateTime.new_now_utc().to_unix_usec()}.png")
    elif isinstance(v, Gdk.FileList) or isinstance(v, Gio.ListStore):
        for file in v:
            if file.has_prefix(app_data): continue
            f, n = m.get_child(file.get_basename()), 1
            while os.path.exists(f.peek_path()):
                n += 1
                f = m.get_child(f"{file.get_basename()} {n}")
            shutil.copytree(file.peek_path(), f.peek_path()) if os.path.isdir(file.peek_path()) else file.copy(f, 0)
def key_pressed(e, kv, kc, s):
    if kv == 118 and s == 4:
        c = app.props.active_window.props.display.get_clipboard()
        if c.props.formats.contain_gtype(Gdk.Texture):
            c.read_texture_async(None, lambda cl, r: add(cl.read_texture_finish(r)))
            return True
        elif c.props.formats.contain_gtype(Gdk.FileList):
            c.read_value_async(Gdk.FileList, 0, None, lambda cl, r: add(cl.read_value_finish(r)))
            return True
controller_key.connect("key-pressed", key_pressed)
t_drop.connect("drop", lambda d, v, *_: add(v))
for i in (controller_key, t_drop): toast_overlay.add_controller(i)
file_filter = Gio.ListStore.new(Gtk.FileFilter)
for n, t in (("All Supported Types", ("image/*", "video/*")), ("Comic Book Archive", ("application/vnd.comicbook+zip",)), ("Image", ("image/*",)), ("Video", ("video/*",))): file_filter.append(Gtk.FileFilter(name=n, mime_types=t))
Action("add-file", (), lambda *_: Gtk.FileDialog(filters=file_filter).open_multiple(app.props.active_window, None, lambda d, r: add(d.open_multiple_finish(r))))
Action("add-folder", (), lambda *_: Gtk.FileDialog().select_folder(app.props.active_window, None, lambda d, r: add((d.select_folder_finish(r),))))
_breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.new_length(1, 700, 0))
_breakpoint.add_setter(split_view, "collapsed", True)
_breakpoint.add_setter(search_layout, "layout-name", "narrow")

delete_dialog = Adw.AlertDialog(default_response="cancel")
delete_dialog.connect("response", lambda d, r: (shutil.rmtree(app.file.peek_path()) if os.path.isdir(app.file.peek_path()) else app.file.delete(), edit.close()) if r == "delete" else None)
for i in ("cancel", "delete"): delete_dialog.add_response(i, i.title())
delete_dialog.set_response_appearance("delete", 2)

edit, edit_page, edit_group = Adw.PreferencesDialog(follows_content_size=True), Adw.PreferencesPage(icon_name="document-edit-symbolic", title="Edit"), Adw.PreferencesGroup()
edit.bind_property("css-classes", edit, "width-request", 0, lambda b, v: 430 if "floating" in v else -1)
edit.add(edit_page)
edit.props.visible_page.add(edit_group)
path, target = Adw.EntryRow(title="Name", show_apply_button=True), Adw.EntryRow(title="Target", name="target")
status = Adw.ToggleGroup(valign=3)
for tooltip, icon in statuses[1:]: status.add(Adw.Toggle(icon_name=icon + "-symbolic", tooltip=tooltip))
status.r = Adw.ActionRow(title="Status", name="status")
status.r.add_suffix(status)
tags = TagRow(name="tags")
dates = tuple(Gtk.Calendar(name=i) for i in ("date", "launched"))
for i in dates:
    i.r = Adw.ActionRow(title=i.props.name.title(), name=i.props.name, css_classes=("property",), subtitle_selectable=True)
    i.bind_property("date", i.r, "subtitle", 0 | 2, lambda b, v: v.to_local().format("%x"))
    i.r.add_suffix(Button(t="menu", css_classes=("flat",), icon_name="month", popover=Gtk.Popover(child=i), valign=3, tooltip_text="Pick a Date"))
hidden = Adw.SwitchRow(title="Hidden", name="hidden")
def edit_changed(*_):
    if app.modifying: return
    for r, i, p in properties[1:]:
        if r.props.visible:
            if r.props.name in app.data[0][app_data.get_relative_path(app.file)]:
                v = getattr(i.props, i.p)
                app.data[0][app_data.get_relative_path(app.file)][r.props.name] = v if not isinstance(v, GLib.DateTime) else v.to_utc().to_unix()
    if path.props.text != app.file.get_basename():
        f = app.file.get_parent().get_child(path.props.text)
        if os.path.exists(f.peek_path()): return edit.add_toast(Adw.Toast(title=f"{f.get_basename()} already exists"))
        app.file.move(f, 0)
        edit.close()
notes_row = (a := Adw.PreferencesPage(icon_name="accessories-text-editor-symbolic", title="Notes"), edit.add(a), g := Adw.PreferencesGroup(), a.add(g), r := Adw.PreferencesRow(child=Gtk.TextView(css_classes=("notes",)), name="notes"), g.add(r), r)[-1]
notes_row.bind_property("visible", edit.get_template_child(Adw.PreferencesDialog, "view_switcher_stack"), "visible-child", 0 | 2, lambda b, v: edit.get_template_child(Adw.PreferencesDialog, "view_switcher_stack").props.pages[0 if v else 1].props.child)
properties = ((path, path, ("text", "apply")),
             (target, target, ("text", "changed")),
             (status.r, status, ("active", "notify::active")),
             (hidden, hidden, ("active", "notify::active")),
             (dates[0].r, dates[0], ("date", "notify::date")),
             (dates[1].r, dates[1], ("date", "notify::date")),
             (tags, tags, ("tags", "notify::tags")),
             (notes_row, notes_row.props.child.props.buffer, ("text", "changed")),)
for r, i, p in properties:
    i.p = p[0]
    i.connect(p[1], edit_changed)
    if r != notes_row: edit_group.add(r)
cover_button = Adw.ButtonRow()
cover_button.bind_property("title", cover_button, "css-classes", 0, lambda b, v: ("button", "activatable", "suggested-action" if v == "Select Cover" else "destructive-action",))
def edit_cover(d, r=False):
    c_file = app_data.get_child(app_data.get_relative_path(app.file).replace(GLib.DIR_SEPARATOR_S, " @ "))
    if r:
        file = d.open_finish(r)
        file.copy(c_file, 0)
    else:
        if not os.path.exists(c_file.peek_path()): return Gtk.FileDialog(default_filter=file_filter[2]).open(app.props.active_window, None, edit_cover)
        c_file.delete()
    edit.close()
for i, c in ((cover_button, edit_cover), (Adw.ButtonRow(css_classes=("button", "activatable", "destructive-action"), title="Delete"), lambda *_: delete_dialog.present(app.props.active_window))):
    i.connect("activated", c)
    edit_group.add(i)
Action("open-folder", ("<primary>o",), lambda *_: (file_launcher.set_file(f_catalog.file if f_catalog.get_mapped() else sidebar.props.selected_item.file if sidebar.props.selected_item else app_data), file_launcher.launch()))
app_data = Gio.File.new_for_path(os.path.join(GLib.get_user_data_dir(), about.props.application_name.lower()))
app.all_files, data_file = [], app_data.get_child(about.props.application_name)
if not os.path.exists(app_data.peek_path()): app_data.make_directory()
app.data = marshal.loads(app_data.get_child(about.props.application_name).load_contents()[1]) if os.path.exists(data_file.peek_path()) else ({}, {})
for n, v in (("default-width", 600), ("default-height", 600), ("maximized", False), ("colors", True), ("launch-targets", True), ("exit-launch", False), ("clear-unused", False), ("hidden", False), ("sort", sorts[0])): app.data[-1].setdefault(n, v)
for i in tuple(app.data[-1])[3:8]: app.add_action(Gio.SimpleAction.new_stateful(i, None, GLib.Variant("b", app.data[-1][i])))
app.add_action(Gio.SimpleAction.new_stateful("sort", GLib.VariantType("s"), GLib.Variant("s", app.data[-1]["sort"])))
app.set_accels_for_action("app.hidden", ["<primary>h"])
for i in ("hidden", "sort"): app.lookup_action(i).connect("notify::state", do_search)
app.lookup_action("hidden").bind_property("state", sidebar, "filter", 0 | 2, lambda b, v: free_filter if v.get_boolean() else no_h_filter)
app.connect("activate", lambda a: a.props.active_window.present() if a.props.active_window else (w := Adw.ApplicationWindow(application=a, content=toast_overlay, title=about.props.application_name, default_width=app.data[-1]["default-width"], default_height=app.data[-1]["default-height"], maximized=app.data[-1]["maximized"]), w.add_breakpoint(_breakpoint), w.present())[-1])
app.connect("window-removed", lambda a, w: tuple(app.data[-1].update({i: getattr(w.props, i)}) for i in app.data[-1] if hasattr(w.props, i)))
def changed(m, f, o, e, s=False):
    if app.modifying or f.get_basename().startswith(".goutputstream") or e == 9 and (o and o.has_prefix(app_data)): return
    if f.has_prefix(app_data) and (o and o.has_prefix(app_data)):
        e = 8
    if e == 8:
        for i in tuple(i for i in app.all_files if i.equal(f) or i.has_prefix(f)):
            nf = o if i.equal(f) else o.get_child(f.get_relative_path(i))
            if not app_data.get_relative_path(i) in app.data[0]: continue
            app.data[0][app_data.get_relative_path(nf)] = app.data[0].pop(app_data.get_relative_path(i))
            for it in tuple(it for it in app.all_files if it.has_parent(app_data) and it.get_basename() == app_data.get_relative_path(i).replace(GLib.DIR_SEPARATOR_S, " @ ")): it.move(app_data.get_child(app_data.get_relative_path(nf).replace(GLib.DIR_SEPARATOR_S, " @ ")), Gio.FileCopyFlags.OVERWRITE)
        if e == 8:
            changed(m, f, None, 10, True)
            changed(m, o, None, 9, True)
    if f and e in (10, 2):
        for i in tuple(i for i in app.all_files if i.equal(f) or i.has_prefix(f)):
            if hasattr(i, "m"): i.m.cancel()
            app.all_files.remove(i)
            if f.has_parent(app_data) and not s:
                for i in catalog.h:
                    if app_data.get_relative_path(catalog.h[i].file).replace(GLib.DIR_SEPARATOR_S, " @ ") == f.get_basename(): return Gio.Task.new(catalog.h[i]).run_in_thread(load_picture)
                GLib.idle_add(sidebar_section)
    if f and e in (9, 3):
        if not tuple(i for i in app.all_files if i.equal(f)):
            if f.has_parent(app_data): f_info(app_data, l=(f.get_basename(),))
            else: f_info(tuple(i for i in app.all_files if f.has_parent(i))[0], l=(f.get_basename(),))
            if f.has_parent(app_data) and not s:
                for i in catalog.h:
                    if app_data.get_relative_path(catalog.h[i].file).replace(GLib.DIR_SEPARATOR_S, " @ ") == f.get_basename(): return Gio.Task.new(catalog.h[i]).run_in_thread(load_picture)
                GLib.idle_add(sidebar_section)
    if e in (2, 3, 8, 9, 10) and not s and app.props.active_window:
        GLib.idle_add(do_search)
        if f_catalog.get_mapped():
            set_file(f_catalog.file)
            load_f_catalog(f_catalog.file)
def f_info(d, l=False):
    if not hasattr(d, "m"):
        d.m = d.monitor(Gio.FileMonitorFlags.WATCH_MOVES)
        d.m.connect("changed", changed)
    li = l if l else os.listdir(d.peek_path())
    if hasattr(d, "parent") and d.parent == app_data and not app_data.get_relative_path(d) in app.data[0]:
        app.data[0][app_data.get_relative_path(d)] = {"id": max(tuple(app.data[0][i]["id"] for i in app.data[0] if "id" in app.data[0][i]), default=0) + 1, "hidden": False, "notes": ""}
    for i in sorted(li, key=lambda i: GLib.utf8_collate_key_for_filename(i, -1)):
        f = d.get_child(i)
        f.parent = d
        if os.path.isdir(f.peek_path()):
            if not d == app_data and not d.parent == app_data: continue
            f_info(f)
        elif not (i.endswith(".cbz") or Gio.content_type_guess(i)[0].startswith(("video", "image")) or d == app_data): continue
        app.all_files.append(f)
        if not d == app_data and d.parent == app_data and not app_data.get_relative_path(f) in app.data[0]:
            app.data[0][app_data.get_relative_path(f)] = {"date": int(os.path.getmtime(f.peek_path())), "hidden": False, "launched": GLib.DateTime.new_now_utc().to_unix(), "status": 0, "target": "", "tags": [], "notes": ""}
            toast_overlay.add_toast(Adw.Toast(timeout=2, title=f"{f.get_basename()} added"))
f_info(app_data)
sidebar_section()
do_search()
def shutdown(*_):
    if app.lookup_action("clear-unused").props.state:
        for i in tuple(i for i in app.data[0]):
            if not os.path.exists(app_data.get_child(i).peek_path()): del app.data[0][i]
    for i in app.data[-1]:
        if app.lookup_action(i):
            s = app.lookup_action(i).props.state
            app.data[-1][i] = s.get_boolean() if not i == "sort" else s.get_string()
    data_file.replace_contents(marshal.dumps(app.data), None, True, 0)
app.connect("shutdown", shutdown)
app.run()
