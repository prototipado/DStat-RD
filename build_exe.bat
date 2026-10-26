@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "SPEC=%PROJECT_ROOT%DStat-GUI-dev2.spec"

if not defined PYTHON_EXE (
    if exist "%PROJECT_ROOT%..\.venv\Scripts\python.exe" (
        set "PYTHON_EXE=%PROJECT_ROOT%..\.venv\Scripts\python.exe"
    ) else if exist "%PROJECT_ROOT%.venv\Scripts\python.exe" (
        set "PYTHON_EXE=%PROJECT_ROOT%.venv\Scripts\python.exe"
    ) else (
        set "PYTHON_EXE=python"
    )
)

"%PYTHON_EXE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3.10 or newer was not found.
    echo Install it, activate its virtual environment, or set PYTHON_EXE to python.exe.
    pause
    exit /b 1
)

echo Using Python:
"%PYTHON_EXE%" --version

echo Installing application dependencies...
"%PYTHON_EXE%" -m pip install -r "%PROJECT_ROOT%requirements.txt"
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo [ERROR] PyInstaller installation failed.
    pause
    exit /b 1
)

echo Building DStat GUI 2.0...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --distpath "%PROJECT_ROOT%dist" --workpath "%PROJECT_ROOT%build" "%SPEC%"
if errorlevel 1 (
    echo [ERROR] Build failed. Review the messages above.
    pause
    exit /b 1
)

echo.
echo Build complete:
echo   %PROJECT_ROOT%dist\DStat-GUI-dev2\DStat-GUI-dev2.exe
echo Run the EXE from its folder so PyInstaller can find _internal.
pause
