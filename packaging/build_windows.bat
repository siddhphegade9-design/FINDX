@echo off
REM ===========================================================================
REM  FINDX - build FINDX.exe on Windows 10/11 (64-bit)
REM  Requires Python 3.10-3.13 on PATH.  Run from anywhere:  packaging\build_windows.bat
REM ===========================================================================
setlocal
cd /d "%~dp0.."

echo [1/5] Creating virtual environment .venv-build ...
if exist .venv-build rmdir /s /q .venv-build
python -m venv .venv-build || goto :fail
call .venv-build\Scripts\activate.bat

echo [2/5] Installing dependencies ...
python -m pip install --upgrade pip || goto :fail
pip install -r requirements-dev.txt || goto :fail

echo [3/5] Running the automated test-suite ...
set QT_QPA_PLATFORM=offscreen
python -m pytest || goto :fail
set QT_QPA_PLATFORM=

echo [4/5] Building the executable with PyInstaller ...
pyinstaller packaging\FINDX.spec --noconfirm --clean || goto :fail

echo [5/5] Testing the packaged executable (independent of this Python environment) ...
call .venv-build\Scripts\deactivate.bat
del "%TEMP%\findx_selftest.txt" 2>nul
start /wait "" "dist\FINDX\FINDX.exe" --selftest
set RC=%ERRORLEVEL%
if exist "%TEMP%\findx_selftest.txt" type "%TEMP%\findx_selftest.txt"
if not "%RC%"=="0" goto :fail

copy /y README.md dist\FINDX\README.md >nul
copy /y docs\PROJECT_REPORT.pdf dist\FINDX\PROJECT_REPORT.pdf >nul
echo.
echo BUILD SUCCEEDED:  dist\FINDX\FINDX.exe
exit /b 0

:fail
echo.
echo BUILD FAILED - see messages above.
exit /b 1
