@echo off
setlocal

rem Change to the directory where this script is located
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo.
echo === Publish Options ===
echo 1. Standalone (self-contained, no .NET runtime needed) - recommended
echo 2. Framework-dependent (requires .NET 8.0 Desktop Runtime)
set /p choice="Select option (1 or 2, default 1): "
if "%choice%"=="" set choice=1

if "%choice%"=="1" (
    echo Publishing standalone...
    dotnet publish MouseMasterClone.csproj -c Release -r win-x64 --self-contained true ^
        /p:PublishSingleFile=true ^
        /p:PublishReadyToRun=true ^
        /p:IncludeNativeLibrariesForSelfExtract=true ^
        /p:PublishTrimmed=false
    set "PUBLISH_DIR=bin\Release\net8.0-windows\win-x64\publish"
) else (
    echo Publishing framework-dependent...
    dotnet publish MouseMasterClone.csproj -c Release ^
        /p:PublishSingleFile=true ^
        /p:PublishReadyToRun=true
    set "PUBLISH_DIR=bin\Release\net8.0-windows\publish"
)

if errorlevel 1 (
    echo Publish failed.
    pause
    exit /b 1
)

echo.
echo Build published successfully.
echo.
echo === Run Options ===
echo 1. Run now
echo 2. Open folder
echo 3. Exit
set /p runchoice="Select option (1, 2 or 3): "

if "%runchoice%"=="1" (
    echo Starting MouseMasterClone...
    "%PUBLISH_DIR%\MouseMasterClone.exe"
) else if "%runchoice%"=="2" (
    explorer "%PUBLISH_DIR%"
)

endlocal
pause
