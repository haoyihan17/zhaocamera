@echo off
cd /d "%~dp0"
set "PY=D:\zhaocamera_build\.buildenv\Scripts\pythonw.exe"
if not exist "%PY%" set "PY=C:\apps\Anaconda\pythonw.exe"
start "" "%PY%" main.py
