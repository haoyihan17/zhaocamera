# PyInstaller runtime hook: make onnxruntime DLLs discoverable in onefile mode.
import os
import sys

if getattr(sys, "frozen", False):
    base = getattr(sys, "_MEIPASS", None)
    if base:
        capi = os.path.join(base, "onnxruntime", "capi")
        if os.path.isdir(capi):
            try:
                os.add_dll_directory(capi)
            except Exception:
                pass
