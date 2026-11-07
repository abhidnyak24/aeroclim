@echo off
cd /d "%~dp0"
py -3.11 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r pc\requirements.txt
if errorlevel 1 goto fail
echo Setup complete. Read README.md before flashing or powering all sensors.
pause
exit /b 0
:fail
echo Setup failed. Check Python 3.11 installation and internet access. See README for Python 3.12.
pause
exit /b 1
