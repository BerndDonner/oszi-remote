\
@echo off
setlocal enabledelayedexpansion

REM Build script for Windows (Python 3.11+)
REM Usage: double-click or run in cmd.exe

cd /d "%~dp0\..\.."

if exist .venv-build (
  echo Using existing .venv-build
) else (
  py -3.11 -m venv .venv-build || goto :err
)

call .\.venv-build\Scripts\activate.bat || goto :err
python -m pip install -U pip wheel || goto :err
python -m pip install -e . || goto :err
python -m pip install -U pyinstaller || goto :err

rmdir /s /q dist build 2>nul

pyinstaller ^
  --onefile ^
  --name oszi-remote ^
  --collect-all matplotlib ^
  -m scope_noise_hist || goto :err

echo.
echo Build OK: dist\oszi-remote.exe
echo.

exit /b 0

:err
echo.
echo BUILD FAILED
pause
exit /b 1
