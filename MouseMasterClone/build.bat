@echo off
setlocal

rem Change to the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Building MouseMasterClone...
dotnet build MouseMasterClone.csproj -c Release
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)
echo Build succeeded.
pause

endlocal
