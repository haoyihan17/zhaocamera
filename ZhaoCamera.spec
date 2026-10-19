# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

datas = [('ocr_ps.ps1', '.'), ('icon.png', '.')]
binaries = []
hiddenimports = []
for _pkg in ('rapidocr', 'onnxruntime', 'ctranslate2', 'sentencepiece'):
    tmp_ret = collect_all(_pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['pyi_rth_onnx.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# 去掉重复打包的 VC++ 运行时 DLL，改用系统自带，避免混合 CRT 导致 onnxruntime 原生崩溃
_CRT = {
    'msvcp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll',
    'vcruntime140.dll', 'vcruntime140_1.dll', 'vcruntime140_2.dll',
    'concrt140.dll', 'vcomp140.dll',
}
a.binaries = [t for t in a.binaries if os.path.basename(t[0]).lower() not in _CRT]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ZhaoCamera',
    icon='icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
