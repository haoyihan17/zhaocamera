@echo off
setlocal
set "BUILDROOT=D:\zhaocamera_build"
cd /d "%~dp0"

echo [1/4] Preparing build folder at %BUILDROOT% ...
if not exist "%BUILDROOT%" mkdir "%BUILDROOT%"
copy /y main.py "%BUILDROOT%\" >nul
copy /y floating_window.py "%BUILDROOT%\" >nul
copy /y settings_window.py "%BUILDROOT%\" >nul
copy /y capture.py "%BUILDROOT%\" >nul
copy /y ocr.py "%BUILDROOT%\" >nul
copy /y translator.py "%BUILDROOT%\" >nul
copy /y themes.py "%BUILDROOT%\" >nul
copy /y config.py "%BUILDROOT%\" >nul
copy /y workers.py "%BUILDROOT%\" >nul
copy /y autostart.py "%BUILDROOT%\" >nul
copy /y ocr_ps.ps1 "%BUILDROOT%\" >nul
copy /y pyi_rth_onnx.py "%BUILDROOT%\" >nul
copy /y image_viewer.py "%BUILDROOT%\" >nul
copy /y external_open.py "%BUILDROOT%\" >nul
copy /y offline_translate.py "%BUILDROOT%\" >nul
copy /y setup_wizard.py "%BUILDROOT%\" >nul
copy /y selftest.py "%BUILDROOT%\" >nul
copy /y icon.png "%BUILDROOT%\" >nul
copy /y icon.ico "%BUILDROOT%\" >nul
copy /y ZhaoCamera.spec "%BUILDROOT%\" >nul

echo [2/4] Preparing venv (clean, ASCII path) ...
if not exist "%BUILDROOT%\.buildenv\Scripts\python.exe" (
    "C:\apps\Anaconda\python.exe" -m venv "%BUILDROOT%\.buildenv"
)
"%BUILDROOT%\.buildenv\Scripts\python.exe" -m pip install --no-warn-script-location PyQt5 Pillow requests pyinstaller rapidocr onnxruntime ctranslate2 sentencepiece

echo [3/4] Building exe (spec includes RapidOCR + onnxruntime + CRT dedup) ...
pushd "%BUILDROOT%"
"%BUILDROOT%\.buildenv\Scripts\pyinstaller.exe" ZhaoCamera.spec
popd

echo [4/4] Copying result back ...
if not exist "%~dp0dist" mkdir "%~dp0dist"
copy /y "%BUILDROOT%\dist\ZhaoCamera.exe" "%~dp0dist\ZhaoCamera.exe" >nul
if exist "%~dp0config.json" copy /y "%~dp0config.json" "%~dp0dist\config.json" >nul
echo.
echo Done: %~dp0dist\ZhaoCamera.exe
pause
endlocal
