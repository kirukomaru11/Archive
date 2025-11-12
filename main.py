#!/usr/bin/python3
from shutil import copytree
from shutil import rmtree

from AppUtils import *

css = """
.notes { padding: 10px; }

searchbar multi-layout-view > box { border-spacing: 6px; }

masonrybox revealer button { margin: 6px; }

.navigation-sidebar row box > box:last-child > revealer > box { border-spacing: 4px; }
.navigation-sidebar row button { padding: 2px 6px 2px 6px; }

sheet,
navigation-view {
  transition-property: background;
  transition-duration: 250ms;
  transition-timing-function: ease;
}
.colored {
  --scrollbar-outline-color: rgb(0 0 0 / 25%);
  --accent-color: var(--color-1);
  --accent-bg-color: var(--color-1);
  --popover-bg-color: color-mix(in srgb, var(--color-2), var(--window-bg-color) 60%);
  --card-bg-color: rgb(255 255 255 / 4%);
}
.colored sheet,
.colored navigation-view,
.colored overlay-split-view > :last-child:not(.sidebar-pane) {
  background: linear-gradient(
      to bottom right,
      color-mix(in srgb, var(--color-1) 45%, transparent),
      transparent
    ),
    linear-gradient(
      to bottom left,
      color-mix(in srgb, var(--color-2) 45%, transparent),
      transparent
    ),
    linear-gradient(
      to top,
      color-mix(in srgb, var(--color-3) 45%, transparent),
      transparent
    ),
    var(--window-bg-color);
}
.colored overlay-split-view > .sidebar-pane { background: color-mix(in srgb, var(--sidebar-bg-color) 15%, transparent); box-shadow: none; }
"""

sorts = ("Random", "Alphabetical Ascending", "Alphabetical Descending", "Launched Ascending", "Launched Descending", "Date Ascending", "Date Descending")
date_sort = lambda e: app.data["Entries"][app.data_folder.get_relative_path(e)]["Date"]
launched_sort = lambda e: app.data["Entries"][app.data_folder.get_relative_path(e)]["Launched"]
finish_func = lambda p, pp: setattr(p.file, "colors", palette(pp, distance=1.0, black_white=1.4))

def shutdown(*_):
    if app.lookup_action("clear-unused").get_state().unpack():
        for i in tuple(i for i in app.data["Entries"]):
            if not os.path.exists(app.data_folder.get_child(i).peek_path()): del app.data["Entries"][i]
    data_save()
    app.thread.shutdown(wait=True, cancel_futures=True)

app = App(shortcuts={"General": (("Fullscreen", "app.fullscreen"), ("Sidebar", "F9"), ("Search", "app.search"), ("Open Current Folder", "app.open"), ("Paste Image/Files/Folder", "<primary>v"), ("Toggle Hidden", "app.hidden"), ("Keyboard Shortcuts", "app.shortcuts"))},
          shutdown=shutdown,
          application_id="io.github.kirukomaru11.Archive",
          style=css,
          data={
            "Window": { "default-height": 600, "default-width": 600, "maximized": False },
            "View": { "show-hidden": False, "sort": sorts[0], "colors": True },
            "General": { "launch-targets": False, "clear-unused": False, "exit-launch": False },
            "Entries": {}
          })
app.all_files, app.modifying = [], False
Action("open-folder", lambda *_: launch(f_catalog.file if f_catalog.get_mapped() else sidebar.get_selected_item().file if sidebar.get_selected_item() else app.data_folder), "<primary>o")
_breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.new_length(Adw.BreakpointConditionLengthType.MAX_WIDTH, 700, Adw.LengthUnit.PX))
app.window.add_breakpoint(_breakpoint)

def set_file(file):
    app.modifying = True
    app.file = file
    delete_dialog.set_heading(f"Delete {app.file.get_basename()}")
    edit.set_title(app.file.get_basename())
    cover_button.set_properties(title="Erase Cover" if file.parent.has_parent(app.data_folder) and tuple(i for i in app.all_files if i.has_parent(app.data_folder) and i.get_basename() == app.data_folder.get_relative_path(app.file).replace(GLib.DIR_SEPARATOR_S, " @ ")) else "Select Cover", visible=file.parent.has_parent(app.data_folder))
    for o, p in properties:
        o.get_ancestor(Gtk.ListBoxRow).set_visible(o.get_ancestor(Gtk.ListBoxRow).get_title() in app.data["Entries"][app.data_folder.get_relative_path(app.file)] if app.data_folder.get_relative_path(app.file) in app.data["Entries"] else False)
        if o.get_ancestor(Gtk.ListBoxRow).get_visible():
            v = app.data["Entries"][app.data_folder.get_relative_path(app.file)][o.get_ancestor(Gtk.ListBoxRow).get_title()]
            o.set_property(p, GLib.DateTime.new_from_unix_utc(v).to_local() if isinstance(o, Gtk.Calendar) else v)
    if notes_row.get_visible(): notes_row.get_child().get_buffer().set_text(app.data["Entries"][app.data_folder.get_relative_path(app.file)]["Notes"])
    else: edit.set_visible_page(edit_page)
    GLib.idle_add(set_colors, *(file, True))
    app.modifying = False
def do_search(*_):
    if app.modifying: return
    catalog.page, catalog.end = 0, False
    catalog.remove_all()
    catalog.get_next_sibling().set_visible(False)
    if not sidebar.get_selected_item(): return catalog.get_next_sibling().set_properties(title="Add a Category", icon_name="document-new-symbolic", visible=True)
    fs = tuple(i for i in app.all_files if i.has_parent(sidebar.get_selected_item().file))
    if not fs: return catalog.get_next_sibling().set_properties(title="Add an Entry", icon_name="document-new-symbolic", visible=True)
    catalog.c, t, s = [], search_layout.get_child("search").get_text().lower(), search_layout.get_child("status").get_active()
    for f in fs:
        o = app.data["Entries"][app.data_folder.get_relative_path(f)]
        if o["Hidden"] and not app.lookup_action("show-hidden").get_state().unpack() or (t and not t in f"{f.peek_path()} {o['Tags']} {o['Target']} {o['Notes']}".lower()): continue
        elif not s == 0 and not s - 1 == o["Status"]: continue
        catalog.c.append(f)
    if not catalog.c: return catalog.get_next_sibling().set_properties(title="No Results", icon_name="edit-find-symbolic", visible=True)
    s = app.lookup_action("sort").get_state().unpack()
    catalog.c.sort(key=alphabetical_sort if "Alphabetical" in s else date_sort if "Date" in s else launched_sort if "Launched" in s else random_sort, reverse="Descending" in s)
    catalog_load_more(catalog.get_child(), Gtk.PositionType.BOTTOM)
def get_f(file):
    cover = tuple(i for i in app.all_files if i.has_parent(app.data_folder) and i.get_basename() == app.data_folder.get_relative_path(file).replace(GLib.DIR_SEPARATOR_S, " @ "))
    f = cover[0] if cover else file
    if not cover and os.path.isdir(file.peek_path()):
        f = tuple(i for i in app.all_files if i.has_parent(file))[0]
    return f.get_uri(), bool(cover)
edit_func = lambda e, *_: (set_file(e.get_widget().file), edit.present(app.window))
def catalog_load_more(scrolledwindow, position):
    ca = scrolledwindow.get_parent()
    if position == Gtk.PositionType.BOTTOM and not ca.end:
        ca.end = True
        ca.page += 1
        pages = tuple(ca.c[i:i + 30] for i in range(0, len(ca.c), 30))
        if not ca.page > len(pages):
            for file in pages[ca.page - 1]:
                if file.peek_path() in ca.h: GLib.idle_add(ca.add, ca.h[file.peek_path()])
                else:
                    f, c = get_f(file)
                    entry = Media(f, mimetype="image" if c else None, finish_func=finish_func)
                    entry.file = file
                    ca.h[file.peek_path()] = entry
                    GLib.idle_add(ca.add, entry)
                    event = Gtk.EventControllerMotion()
                    event.connect("enter", lambda e, *_: GLib.idle_add(set_colors, *(e.get_widget().file, True)))
                    GLib.idle_add(entry.add_controller, event)
                    event = Gtk.GestureLongPress()
                    event.connect("pressed", edit_func)
                    GLib.idle_add(entry.add_controller, event)
            ca.end = False
def load_f_catalog(file):
    f_catalog.file, f_catalog.page, f_catalog.end = file, 0, False
    f_catalog.c = tuple(i for i in app.all_files if i.has_parent(f_catalog.file))
    f_catalog.remove_all()
    catalog_load_more(f_catalog.get_child(), Gtk.PositionType.BOTTOM)
def catalog_activate(m, c, b):
    if edit.get_mapped(): return
    set_file(c.file if c.file.parent.has_parent(app.data_folder) else f_catalog.file)
    u = app.data["Entries"][app.data_folder.get_relative_path(app.file)]["Target"]
    if app.lookup_action("launch-targets").get_state().unpack() and u:
        if u.startswith("https"): launch(u)
        else: Gio.AppInfo.create_from_commandline(f"flatpak-spawn --host {u}", None, Gio.AppInfoCreateFlags.NONE).launch()
    else:
        if os.path.isdir(c.file.peek_path()):
            load_f_catalog(c.file)
            view.find_page("f").set_title(c.file.get_basename())
            return view.push_by_tag("f")
        launch(c.file)
    Toast(f"{c.file.get_basename()} launched!")
    app.data["Entries"][app.data_folder.get_relative_path(app.file)]["Launched"] = GLib.DateTime.new_now_utc().to_unix()
    if app.lookup_action("exit-launch").get_state().unpack(): app.window.close()
catalog, f_catalog = tuple(MasonryBox(activate=catalog_activate) for _ in range(2))
for i in (catalog, f_catalog):
    i.h = {}
    i.get_child().connect("edge-reached", catalog_load_more)

for i in ("View", "General"):
    for it in app.data[i]:
        a = Action(it, callback=do_search if it in ("sort", "show-hidden") else None, stateful=app.data[i][it])
        a.path = i
        app.persist.append(a)
app.set_accels_for_action("app.show-hidden", ("<primary>h",))

view = Adw.NavigationView()

search_layout = Adw.MultiLayoutView()
_breakpoint.add_setter(search_layout, "layout-name", "narrow")
search_layout.set_child("search", Gtk.SearchEntry(placeholder_text="Search", hexpand=True))
search_layout.get_child("search").connect("stop-search", lambda *_: search_bar.set_search_mode(False))
search_layout.get_child("search").connect("search-changed", do_search)
search_layout.set_child("status", Adw.ToggleGroup())
statuses = (("All", "view-grid"), ("In Progress", "folder-recent"), ("Finished", "selection-mode"), ("Planned", "month"))
for t, i in statuses: search_layout.get_child("status").add(Adw.Toggle(icon_name=i + "-symbolic", tooltip=t))   
search_layout.get_child("status").connect("notify::active", do_search)
search_layout.add_layout(Adw.Layout(content=Gtk.CenterBox(hexpand=True, center_widget=Adw.Clamp(child=Adw.LayoutSlot.new("search"), maximum_size=300), end_widget=Adw.LayoutSlot.new("status")), name="wide"))
narrow = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
narrow.append(Adw.Clamp(child=Adw.LayoutSlot.new("search"), maximum_size=268))
narrow.append(Adw.Bin(child=Adw.LayoutSlot.new("status"), halign=Gtk.Align.CENTER))
search_layout.add_layout(Adw.Layout(content=narrow, name="narrow"))

toolbar, header = Adw.ToolbarView(content=Gtk.Overlay(child=catalog)), Adw.HeaderBar()
toolbar.get_content().add_overlay(Adw.StatusPage())
search_bar = Gtk.SearchBar(child=search_layout)
search_bar.connect_entry(search_layout.get_child("search"))
Action("search", lambda *_: search_bar.set_search_mode(not search_bar.get_search_mode_enabled()), "<primary>f")
for i in (header, search_bar): toolbar.add_top_bar(i)

menu = Menu((("Fullscreen", "fullscreen"), ("Open Current Folder", "open-folder")), ("Sort", ("sort", sorts)), (("Show Hidden", "show-hidden"), ("Launch Targets", "launch-targets"), ("Exit After Launch", "exit-launch"), ("Entry Color Theming", "colors"), ("Clear Unused", "clear-unused")), app.default_menu)

Action("fullscreen", lambda *_: toolbar.set_reveal_top_bars(not toolbar.get_reveal_top_bars()), "F11")
for i in (Button(t=Gtk.MenuButton, icon_name="open-menu", tooltip_text="Menu", menu_model=menu), Button(t=Gtk.ToggleButton, icon_name="edit-find", tooltip_text="Search", bindings=((None, "active", search_bar, "search-mode-enabled", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE),))): header.pack_end(i)

free_filter, no_h_filter = tuple(Gtk.BoolFilter.new(Gtk.ClosureExpression.new(bool, i)) for i in (lambda i: True, lambda i: not app.data["Entries"][app.data_folder.get_relative_path(i.file)]["Hidden"]))
sidebar, s_section = Adw.Sidebar(drop_preload=True, placeholder=Adw.StatusPage(icon_name="tag-outline-add-symbolic", title="Add a Category")), Adw.SidebarSection()
def drop(s, i, v, a):
    if v[0] in app.all_files:
        a, b = app.data_folder.get_relative_path(sidebar.get_item(i).file), app.data_folder.get_relative_path(v[0])
        app.data["Entries"][a]["ID"], app.data["Entries"][b]["ID"] = app.data["Entries"][b]["ID"], app.data["Entries"][a]["ID"]
        GLib.idle_add(sidebar_section)
        return True
def add_drag(w):
    b = w.get_ancestor(Gtk.ListBoxRow).get_child()
    if hasattr(b, "dr") or not w.get_mapped(): return
    b.set_name(w.f.get_basename())
    b.dr = Gtk.DragSource(actions=Gdk.DragAction.COPY, content=Gdk.ContentProvider.new_for_value(Gdk.FileList.new_from_list((w.f,))))
    b.dr.connect("drag-begin", lambda e, d: Gtk.DragIcon.get_for_drag(d).set_child(Gtk.Label(margin_top=10, margin_start=10, label=e.get_widget().get_name(), css_classes=("title-4",))))
    GLib.idle_add(b.add_controller, b.dr)
    e = Gtk.GestureLongPress()
    b.file = w.f
    e.connect("pressed", edit_func)
    GLib.idle_add(b.add_controller, e)
def sidebar_section():
    if app.modifying: return
    app.modifying = True
    s_section.remove_all()
    for i in sorted((i for i in app.all_files if i.has_parent(app.data_folder) and os.path.isdir(i.peek_path())), key=lambda a: app.data["Entries"][app.data_folder.get_relative_path(a)]["ID"]):
        a = Adw.SidebarItem(title=i.get_basename(), drag_motion_activate=False, suffix=Adw.Bin())
        a.file = i
        a.get_suffix().f = i
        a.get_suffix().connect("map", add_drag)
        s_section.append(a)
    sidebar.set_selected(0)
    app.modifying = False
    GLib.idle_add(do_search)
sidebar.connect("drop", drop)
sidebar.setup_drop_target(Gdk.DragAction.COPY, (Gdk.FileList,))
sidebar.append(s_section)
sidebar.connect("notify::selected", do_search)
sidebar_toolbar, sidebar_header = Adw.ToolbarView(content=sidebar), Adw.HeaderBar(title_widget=Adw.WindowTitle(title="Categories"))
def new_category_response(d):
    if not d.get_extra_child().get_text(): return
    f, n = app.data_folder.get_child(d.get_extra_child().get_text()), 1
    while os.path.exists(f.peek_path()):
        n += 1
        f = app.data_folder.get_child(f"{d.get_extra_child().get_text()} {n}")
    f.make_directory()
new_category = EntryDialog(new_category_response, heading="New Category")
sidebar_header.pack_start(Button(tooltip_text="New Category",icon_name="tag-outline-add-symbolic", callback=lambda *_: new_category.present(app.window)))
sidebar_toolbar.add_top_bar(sidebar_header)
split_view = Adw.OverlaySplitView(content=toolbar, sidebar=sidebar_toolbar, pin_sidebar=True)
_breakpoint.add_setter(split_view, "collapsed", True)
search_bar.set_key_capture_widget(split_view)
Action("sidebar", lambda *_: split_view.set_show_sidebar(not split_view.get_show_sidebar()), "F9")
for i in ((Button(t=Gtk.MenuButton, icon_name="list-add", tooltip_text="Add", menu_model=Menu((("Add File", "add-file"), ("Add Folder", "add-folder"),)))), Button(t=Gtk.ToggleButton, icon_name="sidebar-show", tooltip_text="Sidebar", bindings=((None, "active", split_view, "show-sidebar", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.BIDIRECTIONAL | GObject.BindingFlags.SYNC_CREATE),))): header.pack_start(i)
view.add(Adw.NavigationPage(child=split_view, tag="c"))
app.window.get_content().set_child(view)
sidebar.bind_property("selected-item", view.find_page("c"), "title", 0 | 2, lambda b, v: v.get_title() if v else app.about.get_application_name())

f_toolbar, f_header = Adw.ToolbarView(content=f_catalog), Adw.HeaderBar()
for i in (sidebar_toolbar, f_toolbar): toolbar.bind_property("reveal-top-bars", i, "reveal-top-bars", 0)
f_header.pack_end(Button(t=Gtk.MenuButton, icon_name="open-menu", tooltip_text="Menu", menu_model=menu))
f_header.pack_start(Button(icon_name="list-add", tooltip_text="Add", action_name="app.add-file"))
f_toolbar.add_top_bar(f_header)
view.add(Adw.NavigationPage(child=f_toolbar, tag="f"))

drop = Gtk.DropTarget(preload=True, actions=Gdk.DragAction.COPY, formats=Gdk.ContentFormats.parse("GdkTexture GdkFileList"))
drop.connect("drop", lambda d, v, *_: add(v))
view.add_controller(drop)
def paste(*_):
    c = app.window.get_display().get_clipboard()
    if c.get_formats().contain_gtype(Gdk.Texture):
        c.read_texture_async(None, lambda cl, r: add(cl.read_texture_finish(r)))
        return True
    elif c.get_formats().contain_gtype(Gdk.FileList):
        c.read_value_async(Gdk.FileList, 0, None, lambda cl, r: add(cl.read_value_finish(r)))
        return True
view.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<primary>v"), Gtk.CallbackAction.new(paste)))
def add(v):
    if not sidebar.get_selected_item():
        app.data_folder.get_child("New Category").make_directory()
        sidebar.set_selected(0)
    m = f_catalog.file if f_catalog.get_mapped() else sidebar.get_selected_item().file
    if isinstance(v, Gdk.Texture): v.save_to_png(os.path.join(m, f"{GLib.DateTime.new_now_utc().to_unix_usec()}.png"))
    elif isinstance(v, Gdk.FileList) or isinstance(v, Gio.ListStore):
        for file in v:
            if file.has_prefix(app.data_folder): continue
            f, n = m.get_child(file.get_basename()), 1
            while os.path.exists(f.peek_path()):
                n += 1
                f = m.get_child(f"{file.get_basename()} {n}")
            copytree(file.peek_path(), f.peek_path()) if os.path.isdir(file.peek_path()) else file.copy(f, Gio.FileCopyFlags.NONE)

file_filter = Gio.ListStore.new(Gtk.FileFilter)
for n, t in (("All Supported Types", ("image/*", "video/*")), ("Comic Book Archive", ("application/vnd.comicbook+zip",)), ("Image", ("image/*",)), ("Video", ("video/*",))): file_filter.append(Gtk.FileFilter(name=n, mime_types=t))
Action("add-file", lambda *_: Gtk.FileDialog(filters=file_filter).open_multiple(app.window, None, lambda d, r: add(d.open_multiple_finish(r))))
Action("add-folder", lambda *_: Gtk.FileDialog().select_folder(app.window, None, lambda d, r: add((d.select_folder_finish(r),))))

delete_dialog = Adw.AlertDialog(default_response="cancel")
delete_dialog.connect("response", lambda d, r: (rmtree(app.file.peek_path() if os.path.isdir(app.file.peek_path()) else app.file.delete(), edit.close()) if r == "confirm" else None))
for i in ("cancel", "confirm"): delete_dialog.add_response(i, i.title())
delete_dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE)

edit, edit_page, edit_group = Adw.PreferencesDialog(follows_content_size=True), Adw.PreferencesPage(icon_name="document-edit-symbolic", title="Edit"), Adw.PreferencesGroup()
edit.bind_property("css-classes", edit, "width-request", GObject.BindingFlags.DEFAULT, lambda b, v: 430 if "floating" in v else -1)
edit.add(edit_page)
edit.get_visible_page().add(edit_group)
path, target = Adw.EntryRow(title="Name", show_apply_button=True), Adw.EntryRow(title="Target")
edit.bind_property("title", path, "text", GObject.BindingFlags.DEFAULT)
status = Adw.ToggleGroup(valign=3)
for tooltip, icon in statuses[1:]: status.add(Adw.Toggle(icon_name=icon + "-symbolic", tooltip=tooltip))
status.r = Adw.ActionRow(title="Status")
status.r.add_suffix(status)
tags = TagRow(title="Tags")
dates = tuple(DateRow(title=i) for i in ("Date", "Launched"))
hidden = Adw.SwitchRow(title="Hidden")
def edit_changed(*_):
    if app.modifying: return
    for o, p in properties:
        if o.get_ancestor(Gtk.ListBoxRow).get_visible():
            if o.get_ancestor(Gtk.ListBoxRow).get_title() in app.data["Entries"][app.data_folder.get_relative_path(app.file)]:
                v = o.get_property(p)
                app.data["Entries"][app.data_folder.get_relative_path(app.file)][o.get_ancestor(Gtk.ListBoxRow).get_title()] = v if not isinstance(v, GLib.DateTime) else v.to_utc().to_unix()
    if notes_row.get_visible():
        app.data["Entries"][app.data_folder.get_relative_path(app.file)]["Notes"] = notes_row.get_child().get_buffer().get_property("text")
    if path.get_text() != app.file.get_basename():
        f = app.file.get_parent().get_child(path.get_text())
        if os.path.exists(f.peek_path()): return Toast(f"{f.get_basename()} already exists")
        app.file.move(f, Gio.FileCopyFlags.NONE)
        edit.close()
path.connect("apply", edit_changed)
edit_group.add(path)
notes_row = (a := Adw.PreferencesPage(icon_name="accessories-text-editor-symbolic", title="Notes"), edit.add(a), g := Adw.PreferencesGroup(), a.add(g), r := Adw.PreferencesRow(child=Gtk.TextView(css_classes=("notes",)),), g.add(r), r)[-1]
hidden.bind_property("visible", notes_row, "visible", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE)
notes_row.bind_property("visible", edit.get_template_child(Adw.PreferencesDialog, "view_switcher_stack"), "visible-child", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE, lambda b, v: edit.get_template_child(Adw.PreferencesDialog, "view_switcher_stack").get_pages()[0 if v else 1].get_child())
notes_row.get_child().get_buffer().connect("notify::text", edit_changed)
properties = ((target, "text"),
             (dates[0].calendar, "date"),
             (dates[1].calendar, "date"),
             (hidden, "active"),
             (tags, "tags"),)
for o, p in properties:
    o.connect(f"notify::{p}", edit_changed)
    edit_group.add(o.get_ancestor(Gtk.ListBoxRow))
cover_button = Adw.ButtonRow()
cover_button.bind_property("title", cover_button, "css-classes", GObject.BindingFlags.DEFAULT, lambda b, v: ("button", "activatable", "suggested-action" if v == "Select Cover" else "destructive-action",))
def edit_cover(d, r=False):
    c_file = app.data_folder.get_child(app.data_folder.get_relative_path(app.file).replace(GLib.DIR_SEPARATOR_S, " @ "))
    if r:
        file = d.open_finish(r)
        file.copy(c_file, 0)
    else:
        if not os.path.exists(c_file.peek_path()): return Gtk.FileDialog(default_filter=file_filter[2]).open(app.window, None, edit_cover)
        c_file.delete()
    edit.close()
for i, c in ((cover_button, edit_cover), (Adw.ButtonRow(css_classes=("button", "activatable", "destructive-action"), title="Delete"), lambda *_: delete_dialog.present(app.window))):
    i.connect("activated", c)
    edit_group.add(i)

def changed(m, f, o, e, s=False):
    if app.modifying or f.get_basename().startswith(".goutputstream") or (f.get_basename() in (app.name, f"{app.name}~") and f.has_parent(app.data_folder)): return
    if f.has_prefix(app.data_folder) and (o and o.has_prefix(app.data_folder)):
        e = Gio.FileMonitorEvent.RENAMED
    if e == Gio.FileMonitorEvent.RENAMED:
        for i in tuple(i for i in app.all_files if i.equal(f) or i.has_prefix(f)):
            nf = o if i.equal(f) else o.get_child(f.get_relative_path(i))
            if not app.data_folder.get_relative_path(i) in app.data["Entries"]: continue
            app.data["Entries"][app.data_folder.get_relative_path(nf)] = app.data["Entries"].pop(app.data_folder.get_relative_path(i))
            for it in tuple(it for it in app.all_files if " @ " in it.peek_path() and it.has_parent(app.data_folder) and it.get_basename() == app.data_folder.get_relative_path(i).replace(GLib.DIR_SEPARATOR_S, " @ ") and os.path.exists(it.peek_path())): it.move(app.data_folder.get_child(app.data_folder.get_relative_path(nf).replace(GLib.DIR_SEPARATOR_S, " @ ")), Gio.FileCopyFlags.OVERWRITE)
        if e == Gio.FileMonitorEvent.RENAMED:
            changed(m, f, None, Gio.FileMonitorEvent.MOVED_OUT, True)
            changed(m, o, None, Gio.FileMonitorEvent.MOVED_IN, False)
            return
    catalog_update(f, s)
    if not s and app.get_active_window():
        if f_catalog.get_mapped():
            set_file(f_catalog.file)
            load_f_catalog(f_catalog.file)
def catalog_update(f, s):
    if os.path.exists(f.peek_path()): f_info(tuple(i for i in app.all_files if f.has_parent(i))[0])
    else:
        for i in tuple(i for i in app.all_files if i.equal(f) or i.has_prefix(f)):
            if hasattr(i, "m"): i.m.cancel()
            app.all_files.remove(i)
    if f.has_parent(app.data_folder) and not s:
        for i in catalog.h:
            if app.data_folder.get_relative_path(catalog.h[i].file).replace(GLib.DIR_SEPARATOR_S, " @ ") == f.get_basename():
                p = get_f(catalog.h[i].file)
                app.thread.submit(load_image, catalog.h[i], p[0], "image" if p[1] else None, finish_func)
        GLib.idle_add(sidebar_section)
def f_info(d):
    if not hasattr(d, "m"):
        d.m = d.monitor(Gio.FileMonitorFlags.WATCH_MOVES)
        d.m.connect("changed", changed)
    if d.has_parent(app.data_folder) and not app.data_folder.get_relative_path(d) in app.data["Entries"]:
        app.data["Entries"][app.data_folder.get_relative_path(d)] = {"ID": max(tuple(app.data["Entries"][i]["ID"] for i in app.data["Entries"] if "ID" in app.data["Entries"][i]), default=0) + 1, "Hidden": False, "Notes": ""}
    for i in sorted(os.listdir(d.peek_path()), key=alphabetical_sort):
        f = d.get_child(i)
        f.parent = d
        if os.path.isdir(f.peek_path()):
            if hasattr(d, "parent") and not d.parent.equal(app.data_folder): continue
            f_info(f)
        elif not (i.endswith(".cbz") or Gio.content_type_guess(i)[0].startswith(("video", "image")) or d.equal(app.data_folder)): continue
        if not tuple(it for it in app.all_files if it.equal(f)): app.all_files.append(f)
        if not d.equal(app.data_folder) and d.parent == app.data_folder and not app.data_folder.get_relative_path(f) in app.data["Entries"]:
            app.data["Entries"][app.data_folder.get_relative_path(f)] = {"Date": int(os.path.getmtime(f.peek_path())), "Launched": GLib.DateTime.new_now_utc().to_unix(), "Status": 0, "Hidden": False, "Target": "", "Notes": "", "Tags": []}
            Toast(f"{f.get_basename()} added", timeout=2)
    if not tuple(it for it in app.all_files if it.equal(d)): app.all_files.append(d)
f_info(app.data_folder)
app.lookup_action("show-hidden").bind_property("state", sidebar, "filter", GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE, lambda b, v: free_filter if v.get_boolean() else no_h_filter)
GLib.idle_add(sidebar_section)
app.run()
