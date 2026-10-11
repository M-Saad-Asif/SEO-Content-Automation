@echo off
rem Windows: double-click this file, or run it in a terminal. It finds Python and runs install.py.
cd /d "%~dp0"
where py >nul 2>nul && (py -3 install.py %* & goto end)
where python >nul 2>nul && (python install.py %* & goto end)
echo Python 3.10+ is needed: install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH"), then run this again.
:end
pause
