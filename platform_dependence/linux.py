import os
import json
import subprocess
import shutil

_last_krita_status = None
_krita_is_on_callback = None
_krita_is_off_callback = None
_krita_is_unk_callback = None

def delimiter_conversion(path: str) -> str:
    return path.replace('\\', '/')

def get_default_k_r_path() -> str:
    # Check Flatpak Krita resource path first, fallback to standard ~/.local/share/krita
    flatpak_path = os.path.expanduser('~/.var/app/org.kde.krita/data/krita')
    if os.path.exists(flatpak_path) or os.path.exists(os.path.expanduser('~/.var/app/org.kde.krita')):
        return flatpak_path
    return os.path.expanduser('~/.local/share/krita')

def get_app_icon() -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        '/app/share/icons/hicolor/512x512/apps/com.github.krita_manage_tool.png',
        os.path.join(base_dir, 'icon.png'),
        os.path.join(base_dir, 'resources', 'icon.png'),
        os.path.join(os.getcwd(), 'icon.png')
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(base_dir, 'resources', 'icon.png')

def apply_theme_to_titlebar(master):
    pass

def set_krita_is_on_callback(callback):
    global _krita_is_on_callback
    _krita_is_on_callback = callback

def set_krita_is_off_callback(callback):
    global _krita_is_off_callback
    _krita_is_off_callback = callback

def set_krita_is_unk_callback(callback):
    global _krita_is_unk_callback
    _krita_is_unk_callback = callback

def check_krita():
    """Check if Krita is running on Linux using pgrep or pidof"""
    try:
        res = subprocess.run(['pgrep', '-x', 'krita'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    except Exception:
        try:
            res = subprocess.run(['pidof', 'krita'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return res.returncode == 0
        except Exception:
            return None

def update_krita_status():
    """Background GLib / thread status updates for Krita"""
    import threading
    def _check():
        global _last_krita_status
        while True:
            is_running = check_krita()
            if is_running is False and _last_krita_status != is_running:
                _last_krita_status = is_running
                if _krita_is_off_callback:
                    _krita_is_off_callback()
            elif is_running is True and _last_krita_status != is_running:
                _last_krita_status = is_running
                if _krita_is_on_callback:
                    _krita_is_on_callback()
            elif is_running is None and _last_krita_status != is_running:
                _last_krita_status = is_running
                if _krita_is_unk_callback:
                    _krita_is_unk_callback()
            threading.Event().wait(0.5)

    threading.Thread(target=_check, daemon=True).start()

def _get_linux_config_files():
    # Linux Krita config files (checks Flatpak sandbox ~/.var/app/org.kde.krita/config first)
    flatpak_cfg = os.path.expanduser('~/.var/app/org.kde.krita/config')
    config_home = flatpak_cfg if os.path.exists(flatpak_cfg) else os.path.expanduser('~/.config')
    
    files = [
        os.path.join(config_home, 'kritarc'),
        os.path.join(config_home, 'kritadisplayrc'),
        os.path.join(config_home, 'kritashortcutsrc'),
        os.path.join(config_home, 'krita.log'),
        os.path.join(config_home, 'kritacrash.log'),
        os.path.join(config_home, 'krita-sysinfo.log'),
    ]
    
    # Also include native ~/.config files if flatpak config dir exists
    if config_home != os.path.expanduser('~/.config'):
        native_cfg = os.path.expanduser('~/.config')
        for fname in ['kritarc', 'kritadisplayrc', 'kritashortcutsrc', 'krita.log', 'kritacrash.log', 'krita-sysinfo.log']:
            files.append(os.path.join(native_cfg, fname))
            
    return files

def _make_no_username_path(path: str) -> str:
    home = os.path.expanduser('~')
    if path.startswith(home):
        return path.replace(home, '{$USERDIR}', 1)
    return path

def _add_username_path(path: str) -> str:
    home = os.path.expanduser('~')
    return path.replace('{$USERDIR}', home)

def get_default_save_path() -> str:
    return os.path.expanduser('~/Documents/krita-config-tool')

def get_storage_base_dir() -> str:
    import json_manage
    save_path = json_manage.settings_manager.get_setting('config_save_path')
    if not save_path:
        save_path = get_default_save_path()
    os.makedirs(save_path, exist_ok=True)
    return save_path

def new_krita_config(name: str):
    import json_manage
    base_dir = get_storage_base_dir()
    path = os.path.join(base_dir, name)
    src_path = json_manage.settings_manager.get_setting('krita_resources_path')
    src_path_no_username = _make_no_username_path(src_path)

    try:
        if os.path.exists(src_path):
            shutil.copytree(src_path, os.path.join(path, 'resources'), dirs_exist_ok=True)
        else:
            os.makedirs(os.path.join(path, 'resources'), exist_ok=True)

        os.makedirs(os.path.join(path, 'config'), exist_ok=True)

        for i in _get_linux_config_files():
            if os.path.exists(i):
                shutil.copyfile(i, os.path.join(path, 'config', os.path.basename(i)))

        json_manage.config_manager.new_config(name, src_path_no_username, get_platform_name())
        return True, None
    except Exception as e:
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
        except Exception:
            pass
        return False, str(e)

def _get_path(name: str):
    import json_manage
    base_dir = get_storage_base_dir()
    path = os.path.join(base_dir, name)
    cfg = json_manage.config_manager.get_config(name)
    sre_path = cfg.get('resources_path') if cfg else ""
    return [path, sre_path]

def get_config_path(name: str):
    path, sre_path = _get_path(name)
    return path, _add_username_path(sre_path)

def check_configuration_path(name: str) -> bool:
    import json_manage
    path = get_config_path(name)
    return path[1] == json_manage.settings_manager.get_setting('krita_resources_path')

def reset_krita() -> bool:
    import json_manage
    try:
        res_path = json_manage.settings_manager.get_setting('krita_resources_path')
        if os.path.exists(res_path):
            shutil.rmtree(res_path)
        for i in _get_linux_config_files():
            if os.path.exists(i):
                try:
                    os.remove(i)
                except Exception:
                    pass
        return True
    except Exception:
        return False

def use_krita_config(name: str) -> bool:
    import json_manage
    path, sre_path = _get_path(name)
    sre_path = _add_username_path(sre_path)

    try:
        reset_krita()
        cur_target = get_config_path(name)[1]
        if os.path.exists(cur_target):
            try:
                shutil.rmtree(cur_target)
            except Exception:
                pass

        saved_res = os.path.join(path, 'resources')
        if os.path.exists(saved_res):
            shutil.copytree(saved_res, sre_path, dirs_exist_ok=True)

        saved_cfg_dir = os.path.join(path, 'config')
        if os.path.exists(saved_cfg_dir):
            for i in _get_linux_config_files():
                fname = os.path.basename(i)
                src_file = os.path.join(saved_cfg_dir, fname)
                if os.path.exists(src_file):
                    os.makedirs(os.path.dirname(i), exist_ok=True)
                    shutil.copyfile(src_file, i)

        if json_manage.settings_manager.get_setting('krita_resources_path') != sre_path:
            json_manage.settings_manager.set_setting('krita_resources_path', sre_path)
        return True
    except Exception as e:
        print("use_krita_config error:", e)
        return False

def del_krita_config(name: str) -> bool:
    import json_manage
    path = _get_path(name)[0]
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
        json_manage.config_manager.remove_config(name)
        return True
    except Exception as e:
        print("del_krita_config error:", e)
        return False

def output_krita_config(name: str, out_file_path: str):
    import json_manage
    path = get_config_path(name)[0]
    temp_dir = os.path.join(os.getcwd(), 'temp')
    temp_file_path = os.path.join(temp_dir, name)
    os.makedirs(temp_dir, exist_ok=True)
    if os.path.exists(temp_file_path):
        shutil.rmtree(temp_file_path)
    shutil.copytree(path, temp_file_path)
    json_manage.config_manager.output_one_config(name, temp_file_path)
    base_name = out_file_path[:-4] if out_file_path.endswith('.zip') else out_file_path
    shutil.make_archive(base_name, 'zip', temp_file_path)
    shutil.rmtree(temp_file_path)

def extract_krita_config(path: str):
    temp_file_path = os.path.join(os.getcwd(), 'temp', str(os.path.basename(path).replace('.zip', '')))
    if os.path.exists(temp_file_path):
        shutil.rmtree(temp_file_path)
    shutil.unpack_archive(path, temp_file_path)
    cfg_file = os.path.join(temp_file_path, 'configs.json')
    if os.path.exists(cfg_file):
        with open(cfg_file, 'r', encoding='utf-8') as f:
            configs = json.load(f)
            return _add_username_path(configs.get('resources_path', '')), configs.get('platform', ''), configs.get('name', ''), temp_file_path
    return "", "", "", temp_file_path

def input_krita_config(path: str, new_name=None):
    import json_manage
    json_manage.config_manager.input_one_config(os.path.join(path, 'configs.json'), new_name)
    base_dir = get_storage_base_dir()
    target_res = os.path.join(base_dir, new_name, 'resources')
    target_cfg = os.path.join(base_dir, new_name, 'config')
    if os.path.exists(os.path.join(path, 'resources')):
        shutil.copytree(os.path.join(path, 'resources'), target_res, dirs_exist_ok=True)
    if os.path.exists(os.path.join(path, 'config')):
        shutil.copytree(os.path.join(path, 'config'), target_cfg, dirs_exist_ok=True)

def open_config_folder(name: str):
    path = get_config_path(name)[0]
    if os.path.exists(path):
        subprocess.Popen(['xdg-open', path])

def get_platform_name() -> str:
    return 'linux'
