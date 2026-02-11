@echo off
setlocal
cd /d "%~dp0"
mkdir logs >nul 2>nul

if "%~1"=="" (
  echo Usage examples:
  echo   oszi-remote --list-ports
  echo   oszi-remote --port COM5 --csv out.csv
  echo.
  echo Verfuegbare Ports:
  oszi-remote.exe --list-ports
  echo.
  echo (Du kannst Parameter auch an dieses Start-Script haengen, z.B.:
  echo   Start_oszi-remote.bat --port COM5 --csv out.csv)
  echo.
  pause
  exit /b 1
)

oszi-remote.exe %* > logs\run.log 2>&1
echo.
echo Log: %~dp0logs\run.log
pause
