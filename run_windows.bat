@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo Khong the cai dependencies. Hay kiem tra Python va Internet.
  pause
  exit /b 1
)
py mc_diag.py
pause
