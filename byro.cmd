@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto :venv
if not exist ".env" goto :env
:dispatch
if "%~1"=="" goto :browse
if /I "%~1"=="setup" goto :setup
if /I "%~1"=="test" goto :test
".venv\Scripts\python.exe" -m app %*
exit /b %errorlevel%

:venv
echo [byro] creating virtualenv...
python -m venv .venv
if errorlevel 1 (
  echo [byro] Python not found - install Python 3.11+ and retry.
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 exit /b 1
if not exist ".env" copy /y ".env.example" ".env" >nul
goto :dispatch

:env
copy /y ".env.example" ".env" >nul
echo [byro] created .env from .env.example
goto :dispatch

:browse
".venv\Scripts\python.exe" -m app browse
exit /b %errorlevel%

:test
".venv\Scripts\python.exe" -m pytest -q
exit /b %errorlevel%

:setup
echo [byro] ready: .venv + .env present
exit /b 0
