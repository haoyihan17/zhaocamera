@echo off
setlocal
cd /d "%~dp0"

rem PyInstaller 在中文路径下找不到 Qt 插件，构建目录必须是纯英文路径。
rem 默认放脚本所在盘的根目录（如 D:\zhaocamera_build），可用 BUILDROOT 环境变量覆盖。
if not defined BUILDROOT set "BUILDROOT=%~d0\zhaocamera_build"

echo [1/4] Preparing build folder: %BUILDROOT%
if not exist "%BUILDROOT%" mkdir "%BUILDROOT%"
for %%f in (main.py floating_window.py settings_window.py setup_wizard.py selftest.py capture.py ocr.py ocr_ps.ps1 translator.py offline_translate.py themes.py config.py workers.py autostart.py image_viewer.py external_open.py pyi_rth_onnx.py icon.png icon.ico ZhaoCamera.spec) do copy /y "%%f" "%BUILDROOT%\" >nul

echo [2/4] Preparing venv (ASCII path) ...
set "BASEPY=python"
if defined PYTHON set "BASEPY=%PYTHON%"
if not exist "%BUILDROOT%\.buildenv\Scripts\python.exe" %BASEPY% -m venv "%BUILDROOT%\.buildenv"
"%BUILDROOT%\.buildenv\Scripts\python.exe" -m pip install --no-warn-script-location PyQt5 Pillow requests pyinstaller rapidocr onnxruntime ctranslate2 sentencepiece

echo [3/4] Building exe ...
pushd "%BUILDROOT%"
"%BUILDROOT%\.buildenv\Scripts\pyinstaller.exe" ZhaoCamera.spec
popd

echo [4/4] Copying result back ...
if not exist "%~dp0dist" mkdir "%~dp0dist"
copy /y "%BUILDROOT%\dist\ZhaoCamera.exe" "%~dp0dist\ZhaoCamera.exe" >nul
echo.
echo Done: %~dp0dist\ZhaoCamera.exe
pause
endlocal
