#!/usr/bin/env python3
import sys
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio, Gdk

import json_manage
import platform_dependence

version = "0.0.4"
developer = "白熊Fx"


class KritaManageApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id='com.github.krita_manage_tool',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_title(json_manage.language_manager.get_static().get('title', 'Krita Configuration Manager'))
        self.set_default_size(780, 520)

        # Set Application Icon
        icon_path = platform_dependence.get_app_icon()
        if os.path.exists(icon_path):
            self.set_icon_name("com.github.krita_manage_tool")
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            icon_theme.add_search_path(os.path.dirname(icon_path))

        # Set up Libadwaita HeaderBar & Navigation Structure
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        # Header Bar
        self.header_bar = Adw.HeaderBar()
        self.main_box.append(self.header_bar)

        # Window Title
        self.header_title = Adw.WindowTitle(title=json_manage.language_manager.get_static().get('title'))
        self.header_bar.set_title_widget(self.header_title)

        # Left Header Button (Refresh/Reload)
        self.refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self.refresh_btn.set_tooltip_text("Reload Configs")
        self.refresh_btn.connect('clicked', lambda x: self.load_configs())
        self.header_bar.pack_start(self.refresh_btn)

        # Right Header Button (Settings)
        self.settings_btn = Gtk.Button(icon_name="emblem-system-symbolic")
        self.settings_btn.set_tooltip_text(json_manage.language_manager.get_data().get('setting', 'Settings'))
        self.settings_btn.connect('clicked', self.on_open_settings)
        self.header_bar.pack_end(self.settings_btn)

        # Adw.Clamp wrapper to keep window compact and pad on larger screens
        self.clamp = Adw.Clamp()
        self.clamp.set_maximum_size(840)
        self.clamp.set_tightening_threshold(780)
        self.clamp.set_vexpand(True)
        self.main_box.append(self.clamp)

        # Main Layout Container: Split into Config List Left and Action Pane Right
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        content_box.set_margin_start(16)
        content_box.set_margin_end(16)
        content_box.set_margin_top(16)
        content_box.set_margin_bottom(16)
        self.clamp.set_child(content_box)

        # Left Column: Configuration List
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left_box.set_hexpand(True)
        content_box.append(left_box)

        list_label = Gtk.Label(label="Configurations", xalign=0)
        list_label.add_css_class("heading")
        left_box.append(list_label)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_height(360)
        scrolled.add_css_class("card")
        left_box.append(scrolled)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect('row-selected', self.on_config_selected)
        scrolled.set_child(self.listbox)

        # Action Buttons under List (+ and -, Open Folder, Reset)
        list_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        left_box.append(list_btn_box)

        self.add_btn = Gtk.Button(icon_name="list-add-symbolic")
        self.add_btn.set_tooltip_text("New Config")
        self.add_btn.connect('clicked', self.on_add_config)
        list_btn_box.append(self.add_btn)

        self.del_btn = Gtk.Button(icon_name="list-remove-symbolic")
        self.del_btn.set_tooltip_text("Delete Selected Config")
        self.del_btn.connect('clicked', self.on_delete_config)
        list_btn_box.append(self.del_btn)

        self.open_folder_btn = Gtk.Button(icon_name="folder-open-symbolic")
        self.open_folder_btn.set_tooltip_text("Open Config Folder in File Manager")
        self.open_folder_btn.connect('clicked', self.on_open_config_folder)
        list_btn_box.append(self.open_folder_btn)

        # Right-aligned Reset Button using a spring spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        list_btn_box.append(spacer)

        self.reset_btn = Gtk.Button(label=json_manage.language_manager.get_static().get('clear', 'Reset Krita'))
        self.reset_btn.add_css_class("destructive-action")
        self.reset_btn.connect('clicked', self.on_reset_krita)
        list_btn_box.append(self.reset_btn)

        # Right Column: Details & Operations
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        right_box.set_size_request(310, -1)
        content_box.append(right_box)

        # Status Group Card
        status_group = Adw.PreferencesGroup()
        status_group.set_title("Krita Status")
        right_box.append(status_group)

        self.status_row = Adw.ActionRow()
        self.status_row.set_title(json_manage.language_manager.get_data().get('state-ex', 'Status: Checking...'))

        self.status_indicator = Gtk.Image(icon_name="media-playback-stop-symbolic")
        self.status_row.add_prefix(self.status_indicator)
        status_group.add(self.status_row)

        # Config Info Card
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Selected Info")
        right_box.append(info_group)

        self.info_name_row = Adw.ActionRow(title="Name", subtitle="None")
        info_group.add(self.info_name_row)

        self.info_path_row = Adw.ActionRow(title="Resources Path", subtitle="-")
        self.info_path_row.set_subtitle_selectable(True)
        info_group.add(self.info_path_row)

        self.info_platform_row = Adw.ActionRow(title="Platform", subtitle="-")
        info_group.add(self.info_platform_row)

        self.info_date_row = Adw.ActionRow(title="Date Created", subtitle="-")
        info_group.add(self.info_date_row)

        # Operational Buttons Card
        op_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        right_box.append(op_box)

        self.apply_btn = Gtk.Button(label=json_manage.language_manager.get_data().get('apply', 'Apply Config'))
        self.apply_btn.add_css_class("suggested-action")
        self.apply_btn.add_css_class("pill")
        self.apply_btn.connect('clicked', self.on_apply_config)
        op_box.append(self.apply_btn)

        import_export_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        import_export_box.set_homogeneous(True)
        op_box.append(import_export_box)

        self.import_btn = Gtk.Button(label=json_manage.language_manager.get_data().get('input', 'Import'))
        self.import_btn.connect('clicked', self.on_import_config)
        import_export_box.append(self.import_btn)

        self.export_btn = Gtk.Button(label=json_manage.language_manager.get_data().get('output', 'Export'))
        self.export_btn.connect('clicked', self.on_export_config)
        import_export_box.append(self.export_btn)

        # Register Callbacks for Krita status check
        platform_dependence.set_krita_is_on_callback(lambda: GLib.idle_add(self.update_status_ui, True))
        platform_dependence.set_krita_is_off_callback(lambda: GLib.idle_add(self.update_status_ui, False))
        platform_dependence.set_krita_is_unk_callback(lambda: GLib.idle_add(self.update_status_ui, None))
        platform_dependence.update_krita_status()

        self.selected_config_name = None
        self.load_configs()

    def retranslate_ui(self):
        self.set_title(json_manage.language_manager.get_static().get('title', 'Krita Configuration Manager'))
        self.header_title.set_title(json_manage.language_manager.get_static().get('title'))
        self.settings_btn.set_tooltip_text(json_manage.language_manager.get_data().get('setting', 'Settings'))
        self.reset_btn.set_label(json_manage.language_manager.get_static().get('clear', 'Reset Krita'))
        self.apply_btn.set_label(json_manage.language_manager.get_data().get('apply', 'Apply Config'))
        self.import_btn.set_label(json_manage.language_manager.get_data().get('input', 'Import'))
        self.export_btn.set_label(json_manage.language_manager.get_data().get('output', 'Export'))
        platform_dependence.update_krita_status()
        self.load_configs()

    def update_status_ui(self, is_running):
        if is_running is True:
            self.status_row.set_title(json_manage.language_manager.get_data().get('state-on'))
            self.status_indicator.set_from_icon_name("media-playback-start-symbolic")
        elif is_running is False:
            self.status_row.set_title(json_manage.language_manager.get_data().get('state-off'))
            self.status_indicator.set_from_icon_name("media-playback-stop-symbolic")
        else:
            self.status_row.set_title(json_manage.language_manager.get_data().get('state-unk'))
            self.status_indicator.set_from_icon_name("dialog-question-symbolic")

    def load_configs(self):
        # Clear existing items in listbox
        while True:
            row = self.listbox.get_row_at_index(0)
            if row is None:
                break
            self.listbox.remove(row)

        configs = json_manage.config_manager.get_all_configs()
        if not configs:
            empty_row = Adw.ActionRow()
            empty_row.set_title("No configurations added yet")
            empty_row.set_subtitle("Click '+' button below to add your first config backup")
            empty_row.set_sensitive(False)
            self.listbox.append(empty_row)
        else:
            for name, data in configs.items():
                row = Adw.ActionRow()
                row.set_title(name)
                row.set_subtitle(f"Platform: {data.get('platform', 'unknown')} | Created: {data.get('time', '')[:10]}")
                row.config_name = name
                self.listbox.append(row)

        self.selected_config_name = None
        self.update_details(None)

    def on_config_selected(self, listbox, row):
        if row and hasattr(row, 'config_name'):
            self.selected_config_name = getattr(row, 'config_name', None)
            self.update_details(self.selected_config_name)
        else:
            self.selected_config_name = None
            self.update_details(None)

    def update_details(self, name):
        if not name:
            self.info_name_row.set_subtitle("None")
            self.info_path_row.set_subtitle("-")
            self.info_platform_row.set_subtitle("-")
            self.info_date_row.set_subtitle("-")
            self.apply_btn.set_sensitive(False)
            self.export_btn.set_sensitive(False)
            self.del_btn.set_sensitive(False)
            self.open_folder_btn.set_sensitive(False)
            return

        cfg = json_manage.config_manager.get_config(name)
        if cfg:
            self.info_name_row.set_subtitle(name)
            self.info_path_row.set_subtitle(cfg.get('resources_path', '-'))
            self.info_platform_row.set_subtitle(cfg.get('platform', '-'))
            raw_time = cfg.get('time', '-')
            formatted_date = raw_time[:10] if len(raw_time) >= 10 else raw_time
            self.info_date_row.set_subtitle(formatted_date)
            self.apply_btn.set_sensitive(True)
            self.export_btn.set_sensitive(True)
            self.del_btn.set_sensitive(True)
            self.open_folder_btn.set_sensitive(True)

    def on_open_config_folder(self, btn):
        if self.selected_config_name:
            platform_dependence.open_config_folder(self.selected_config_name)

    def show_alert(self, title, message):
        dialog = Adw.MessageDialog(heading=title, body=message, transient_for=self)
        dialog.add_response("ok", "OK")
        dialog.present()

    def on_add_config(self, btn):
        dialog = Adw.MessageDialog(heading="New Config", body="Enter configuration name:", transient_for=self)
        entry = Gtk.Entry()
        entry.set_placeholder_text("Config Name")
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)
        dialog.add_response("cancel", json_manage.language_manager.get_data().get('cancel', 'Cancel'))
        dialog.add_response("ok", json_manage.language_manager.get_data().get('ok', 'OK'))
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)

        def response_cb(dlg, response):
            if response == "ok":
                name = entry.get_text().strip()
                if not name:
                    self.show_alert(json_manage.language_manager.get_static().get('error'),
                                    json_manage.language_manager.get_static().get('error-name-empty'))
                    return
                if json_manage.config_manager.get_config(name):
                    msg = json_manage.language_manager.get_static().get('error-name-conflict').replace('{$name}', name)
                    self.show_alert(json_manage.language_manager.get_static().get('error'), msg)
                    return

                success, err = platform_dependence.new_krita_config(name)
                if success:
                    self.load_configs()
                else:
                    self.show_alert(json_manage.language_manager.get_static().get('error'), err or "Failed to create config")

        dialog.connect("response", response_cb)
        dialog.present()

    def on_delete_config(self, btn):
        if not self.selected_config_name:
            self.show_alert(json_manage.language_manager.get_static().get('error'),
                            json_manage.language_manager.get_static().get('error-no-selection'))
            return

        name = self.selected_config_name
        dialog = Adw.MessageDialog(heading="Delete Config",
                                   body=f"Are you sure you want to delete configuration '{name}'?",
                                   transient_for=self)
        dialog.add_response("cancel", json_manage.language_manager.get_data().get('cancel', 'Cancel'))
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def response_cb(dlg, response):
            if response == "delete":
                if platform_dependence.del_krita_config(name):
                    self.load_configs()

        dialog.connect("response", response_cb)
        dialog.present()

    def on_reset_krita(self, btn):
        dialog = Adw.MessageDialog(heading="Reset Krita",
                                   body="Are you sure you want to reset Krita configuration and resource files?",
                                   transient_for=self)
        dialog.add_response("cancel", json_manage.language_manager.get_data().get('cancel', 'Cancel'))
        dialog.add_response("reset", "Reset")
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)

        def response_cb(dlg, response):
            if response == "reset":
                if platform_dependence.reset_krita():
                    self.show_alert("Reset Complete", "Krita resource files have been reset successfully.")

        dialog.connect("response", response_cb)
        dialog.present()

    def on_apply_config(self, btn):
        if not self.selected_config_name:
            self.show_alert(json_manage.language_manager.get_static().get('error'),
                            json_manage.language_manager.get_static().get('error-no-selection'))
            return

        if platform_dependence.check_krita() is True:
            self.show_alert(json_manage.language_manager.get_static().get('error'),
                            json_manage.language_manager.get_static().get('error-krita-is-on'))
            return

        name = self.selected_config_name
        if platform_dependence.use_krita_config(name):
            self.show_alert("Success", f"Configuration '{name}' applied successfully!")
        else:
            self.show_alert(json_manage.language_manager.get_static().get('error'), "Failed to apply configuration.")

    def on_export_config(self, btn):
        if not self.selected_config_name:
            self.show_alert(json_manage.language_manager.get_static().get('error'),
                            json_manage.language_manager.get_static().get('error-no-selection'))
            return

        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Export Config ZIP")
        file_dialog.set_initial_name(f"{self.selected_config_name}.zip")

        def save_cb(dialog, result):
            try:
                gfile = dialog.save_finish(result)
                if gfile:
                    out_path = gfile.get_path()
                    platform_dependence.output_krita_config(self.selected_config_name, out_path)
                    self.show_alert("Export Complete", f"Exported to {out_path}")
            except Exception as e:
                print("Export cancelled or error:", e)

        file_dialog.save(self, None, save_cb)

    def on_import_config(self, btn):
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Import Config ZIP")

        def open_cb(dialog, result):
            try:
                gfile = dialog.open_finish(result)
                if gfile:
                    zip_path = gfile.get_path()
                    res_path, platform, cfg_name, temp_path = platform_dependence.extract_krita_config(zip_path)
                    if platform and platform != platform_dependence.get_platform_name():
                        msg = json_manage.language_manager.get_static().get('error-platform-conflict') \
                            .replace('{$name}', cfg_name).replace('{#config-platform}', platform) \
                            .replace('{#platform}', platform_dependence.get_platform_name())
                        self.show_alert(json_manage.language_manager.get_static().get('error'), msg)
                        return

                    if json_manage.config_manager.get_config(cfg_name):
                        # Name conflict dialog
                        dlg = Adw.MessageDialog(heading="Import Conflict",
                                                body=f"Config '{cfg_name}' already exists. Enter a new name:",
                                                transient_for=self)
                        entry = Gtk.Entry(text=f"{cfg_name}_imported")
                        dlg.set_extra_child(entry)
                        dlg.add_response("ok", "Import")

                        def import_res_cb(d, resp):
                            if resp == "ok":
                                new_name = entry.get_text().strip()
                                platform_dependence.input_krita_config(temp_path, new_name)
                                self.load_configs()

                        dlg.connect("response", import_res_cb)
                        dlg.present()
                    else:
                        platform_dependence.input_krita_config(temp_path, cfg_name)
                        self.load_configs()
            except Exception as e:
                print("Import cancelled or error:", e)

        file_dialog.open(self, None, open_cb)

    def on_open_settings(self, btn):
        dialog = SettingsDialog(transient_for=self)
        dialog.present(self)


class SettingsDialog(Adw.PreferencesDialog):
    def __init__(self, **kwargs):
        super().__init__()
        self.set_title(json_manage.language_manager.get_static().get('title-setting', 'Settings'))

        page = Adw.PreferencesPage()
        self.add(page)

        # General Settings Group
        gen_group = Adw.PreferencesGroup(title="General Settings")
        page.add(gen_group)

        # Krita Resource Path Row
        self.path_row = Adw.ActionRow(title=json_manage.language_manager.get_data().get('krita-resource-path', 'Krita Resources Path'))
        current_path = json_manage.settings_manager.get_setting('krita_resources_path')
        self.path_entry = Gtk.Entry(text=current_path or "")
        self.path_entry.set_valign(Gtk.Align.CENTER)
        self.path_entry.set_hexpand(True)
        self.path_row.add_suffix(self.path_entry)

        browse_btn = Gtk.Button(label=json_manage.language_manager.get_data().get('krita-resource-button', 'Browse'))
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.connect('clicked', self.on_browse_path)
        self.path_row.add_suffix(browse_btn)

        gen_group.add(self.path_row)

        # Backup Storage Folder Path Row
        self.save_path_row = Adw.ActionRow(title="Backup Storage Location")
        curr_save_path = json_manage.settings_manager.get_setting('config_save_path') or platform_dependence.get_default_save_path()
        self.save_path_entry = Gtk.Entry(text=curr_save_path)
        self.save_path_entry.set_valign(Gtk.Align.CENTER)
        self.save_path_entry.set_hexpand(True)
        self.save_path_row.add_suffix(self.save_path_entry)

        save_browse_btn = Gtk.Button(label=json_manage.language_manager.get_data().get('krita-resource-button', 'Browse'))
        save_browse_btn.set_valign(Gtk.Align.CENTER)
        save_browse_btn.connect('clicked', self.on_browse_save_path)
        self.save_path_row.add_suffix(save_browse_btn)

        gen_group.add(self.save_path_row)

        # Language Selection Row
        lang_row = Adw.ActionRow(title=json_manage.language_manager.get_data().get('language', 'Language'))
        self.lang_combo = Gtk.DropDown()
        langs = json_manage.language_manager.scan_language_files()
        lang_names = list(langs.keys())
        self.lang_paths = list(langs.values())

        current_lang_code = json_manage.settings_manager.get_setting('window_language')
        selected_idx = 0
        model = Gtk.StringList()
        for idx, (l_name, l_path) in enumerate(zip(lang_names, self.lang_paths)):
            model.append(l_name)
            if current_lang_code and current_lang_code in os.path.basename(l_path):
                selected_idx = idx

        self.lang_combo.set_model(model)
        self.lang_combo.set_selected(selected_idx)
        self.lang_combo.set_valign(Gtk.Align.CENTER)
        lang_row.add_suffix(self.lang_combo)
        gen_group.add(lang_row)

        # About Group
        about_group = Adw.PreferencesGroup(title=json_manage.language_manager.get_static().get('about-title', 'About'))
        page.add(about_group)

        ver_text = json_manage.language_manager.get_static().get('about-label-l', '').replace('{$version}', version).replace('{$developer}', developer)
        about_row = Adw.ActionRow(title="Krita Reset &amp; Backup Tool", subtitle=ver_text)
        about_group.add(about_row)

        fork_row = Adw.ActionRow(title="Linux Port", subtitle="Forked to Linux by Yiran / 毛艺然")
        about_group.add(fork_row)

        # Save Button
        save_btn_row = Adw.ActionRow()
        save_btn = Gtk.Button(label="Save Settings")
        save_btn.add_css_class("suggested-action")
        save_btn.connect('clicked', self.on_save)
        save_btn_row.set_child(save_btn)
        gen_group.add(save_btn_row)

        self.main_window = kwargs.get('transient_for')

    def on_browse_path(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Krita Resources Folder")

        def select_cb(dlg, result):
            try:
                folder = dlg.select_folder_finish(result)
                if folder:
                    self.path_entry.set_text(folder.get_path())
            except Exception as e:
                print("Folder selection error:", e)

        dialog.select_folder(self, None, select_cb)

    def on_browse_save_path(self, btn):
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Backup Storage Folder")

        def select_cb(dlg, result):
            try:
                folder = dlg.select_folder_finish(result)
                if folder:
                    self.save_path_entry.set_text(folder.get_path())
            except Exception as e:
                print("Folder selection error:", e)

        dialog.select_folder(self, None, select_cb)

    def on_save(self, btn):
        new_path = self.path_entry.get_text().strip()
        if new_path:
            json_manage.settings_manager.set_setting('krita_resources_path', new_path)

        new_save_path = self.save_path_entry.get_text().strip()
        if new_save_path:
            json_manage.settings_manager.set_setting('config_save_path', new_save_path)

        idx = self.lang_combo.get_selected()
        if idx < len(self.lang_paths):
            json_manage.language_manager.reload_for_language(self.lang_paths[idx])

        if self.main_window and hasattr(self.main_window, 'retranslate_ui'):
            self.main_window.retranslate_ui()

        self.close()


def main():
    app = KritaManageApplication()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
