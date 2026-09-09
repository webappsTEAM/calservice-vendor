@echo off
setlocal
echo ======================================================
echo Packaging Codebase into ZIP Archive
echo ======================================================
echo.

set "PY_CMD=python"
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    if exist "%~dp0backend\venv\Scripts\python.exe" (
        set "PY_CMD=%~dp0backend\venv\Scripts\python.exe"
    ) else (
        echo [ERROR] Python is not installed or not in PATH and venv was not found.
        echo Please install Python 3 or add it to your system PATH.
        pause
        exit /b 1
    )
)

"%PY_CMD%" "%~dp0zip_codebase.py" %*

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Codebase zipped successfully!
) else (
    echo.
    echo [ERROR] Zipping failed with error code %ERRORLEVEL%.
)

endlocal
