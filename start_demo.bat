@echo off
cd /d "%~dp0"
.venv\Scripts\python.exe pc\cloudengine.py --simulate
pause
