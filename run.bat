@echo off
rem 启动赵相机。优先项目内 .venv，其次本机开发用的构建环境，最后退回系统 pythonw。
rem 如果 PyQt5 装在别的环境，可以设置 ZHAO_PYTHON 指向那个 pythonw.exe。
cd /d "%~dp0"
set "PY="
if exist ".venv\Scripts\pythonw.exe" set "PY=.venv\Scripts\pythonw.exe"
if not defined PY if defined ZHAO_PYTHON set "PY=%ZHAO_PYTHON%"
if not defined PY if exist "%~d0\zhaocamera_build\.buildenv\Scripts\pythonw.exe" set "PY=%~d0\zhaocamera_build\.buildenv\Scripts\pythonw.exe"
if not defined PY set "PY=pythonw"
start "" "%PY%" main.py
