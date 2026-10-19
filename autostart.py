"""开机自启：写/删 HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run。"""
import os
import sys

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ZhaoCamera"


def _command():
    """返回要注册的开机启动命令行。"""
    if getattr(sys, "frozen", False):
        return '"%s"' % sys.executable
    # 脚本模式：用 pythonw（无黑框）+ main.py
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    pyw = os.path.join(exe_dir, "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    return '"%s" "%s"' % (pyw, main_py)


def enable():
    import winreg
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())
    winreg.CloseKey(key)
    return True


def disable():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass
    except OSError:
        pass
    return True


def is_enabled():
    import winreg
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return bool(val)
    except (FileNotFoundError, OSError):
        return False
