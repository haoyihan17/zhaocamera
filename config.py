"""配置读写模块：config.json 的加载 / 保存，以及打包资源的路径解析。"""
import json
import os
import sys


def base_dir():
    """程序目录：打包后是 exe 所在目录，源码运行时是脚本目录。

    注意：不要把配置写到 sys._MEIPASS（那是临时解包目录，退出即删）。
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(name):
    """只读资源（icon.png / ocr_ps.ps1）：打包后位于 sys._MEIPASS。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def _fallback_config_path():
    """程序目录不可写时的兜底位置（%APPDATA%\\ZhaoCamera\\config.json）。"""
    return os.path.join(os.path.expandvars(r"%APPDATA%"), "ZhaoCamera", "config.json")


BASE_DIR = base_dir()
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULTS = {
    "api_token": "",                       # LM Studio API Token
    "lmstudio_url": "http://127.0.0.1:1234/v1",
    "model": "hy-mt2-1.8b",
    "lms_exe": os.path.expandvars(r"%USERPROFILE%\.lmstudio\bin\lms.exe"),
    "theme": "blue_pink",                  # blue_pink / glass / light / custom
    "opacity": 15,                         # 背景透明度 0-100（越大越透明，文字始终不透明）
    "font_color": "",                      # 字体颜色（空 = 用主题自带配色）
    "font_size": 13,                       # 字体大小 px（9-40）
    "always_on_top": True,                 # 置顶
    "translate_direction": "auto",         # auto / zh2en / en2zh
    "translate_backend": "auto",           # auto（本地→云端→离线）/ local / cloud / offline
    "offline_model_dir": "",               # 离线模型目录（空 = 程序同级的 offline_models）
    "cloud_base_url": "https://api.deepseek.com/v1",
    "cloud_api_key": "",
    "cloud_model": "deepseek-chat",
    "first_run_done": False,               # 是否已完成首次运行引导
    "ocr_engine": "rapidocr",              # rapidocr（深度学习） / windows（轻量）
    "autostart": False,                    # 开机自启
    "custom_bg_path": "",                  # 自定义背景图片路径
    "show_preview": True,                  # 悬浮窗是否显示截图缩略图
}

_config = None
_loaded_from = None


def _read_json(path):
    """读取一个配置文件；损坏时改名备份后返回 None。

    用 utf-8-sig：用户可能用记事本/PowerShell 编辑过，文件会带 UTF-8 BOM，
    用普通 utf-8 解析会整体失败、设置被静默重置。
    """
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        try:
            os.replace(path, path + ".bad")
        except OSError:
            pass
        return None


def load():
    """加载配置（缺失则用默认值）。主目录优先，其次 %APPDATA% 兜底。"""
    global _config, _loaded_from
    cfg = dict(DEFAULTS)
    for path in (CONFIG_PATH, _fallback_config_path()):
        if not os.path.exists(path):
            continue
        data = _read_json(path)
        if data:
            cfg.update(data)
            _loaded_from = path
            break
    _config = cfg
    return cfg


def save(cfg=None):
    """保存配置：主目录优先，不可写则写 %APPDATA%（load 会读回同一位置）。"""
    global _config, _loaded_from
    if cfg is None:
        cfg = _config
    if cfg is None:
        cfg = load()
    data = json.dumps(cfg, ensure_ascii=False, indent=2)
    last_err = None
    for path in (_loaded_from or CONFIG_PATH, CONFIG_PATH, _fallback_config_path()):
        try:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(data)
            _config = cfg
            _loaded_from = path
            return cfg
        except OSError as exc:
            last_err = exc
    raise RuntimeError("配置保存失败（主目录和 %%APPDATA%% 都不可写）：%s" % last_err)


def get(key, default=None):
    if _config is None:
        load()
    return _config.get(key, default)


def get_all():
    if _config is None:
        load()
    return dict(_config)


def set(key, value, save_now=False):
    if _config is None:
        load()
    _config[key] = value
    if save_now:
        save(_config)
    return value
