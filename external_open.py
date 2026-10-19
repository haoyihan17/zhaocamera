"""用 Windows 截图工具打开图片（走应用模型的文件激活 DelegateExecute）。

关键点：
- 截图工具是打包应用，直接跑 exe 或传命令行参数都不加载文件；
- 必须用 ShellExecuteEx，fMask=SEE_MASK_CLASSNAME(0x1) 且 lpClass=它的文件关联 ProgID；
- ProgID 是随包版本变化的哈希值，所以在注册表里动态查找，不硬编码。
"""
import ctypes
import os
import winreg
from ctypes import wintypes

SEE_MASK_CLASSNAME = 0x00000001
SW_SHOWNORMAL = 1

_progid_cache = None


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIcon", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def find_snipping_tool_progid():
    """在 HKCU\\Software\\Classes\\AppX* 里查找截图工具的「文件契约」ProgID。

    同名条目有多个（Windows.Protocol / Windows.File），必须选 ContractId=Windows.File，
    否则会走 URI 协议激活，打开的是空白页。
    """
    global _progid_cache
    if _progid_cache:
        return _progid_cache

    base = r"Software\Classes"
    try:
        root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base)
    except OSError:
        return None

    candidates = []
    i = 0
    try:
        while True:
            try:
                name = winreg.EnumKey(root, i)
            except OSError:
                break
            i += 1
            if not name.startswith("AppX"):
                continue
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    base + "\\" + name + r"\Shell\open") as k:
                    def _get(prop):
                        try:
                            return str(winreg.QueryValueEx(k, prop)[0])
                        except OSError:
                            return ""
                    pkg = _get("PackageId")
                    aumid = _get("AppUserModelID")
                    contract = _get("ContractId")
            except OSError:
                continue
            if "ScreenSketch" in pkg or "ScreenSketch" in aumid:
                candidates.append((contract, name))
    finally:
        winreg.CloseKey(root)

    found = None
    for contract, name in candidates:
        if contract == "Windows.File":
            found = name
            break
    if found is None and candidates:
        found = candidates[0]

    _progid_cache = found
    return found


def shell_execute_open(path, progid):
    """用指定 ProgID 的 open 动作打开文件。"""
    sei = SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_CLASSNAME
    sei.lpVerb = "open"
    sei.lpFile = os.path.abspath(path)
    sei.lpClass = progid
    sei.nShow = SW_SHOWNORMAL
    ok = ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))
    return bool(ok)


def open_in_snipping_tool(path):
    """把图片交给 Windows 截图工具打开（可编辑）。成功返回 True。"""
    progid = find_snipping_tool_progid()
    if not progid:
        return False
    try:
        return shell_execute_open(path, progid)
    except Exception:
        return False


def open_with_default_app(path):
    """回退：用系统默认程序打开。"""
    try:
        os.startfile(os.path.abspath(path))
        return True
    except Exception:
        return False
