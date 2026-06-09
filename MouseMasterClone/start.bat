@echo off
cd /d "%~dp0"

set "EXE=bin\Release\net10.0-windows\win-x64\publish\MouseMasterClone.exe"
if exist "%EXE%" (
    "%EXE%"
    exit /b
)

rem If standalone not found, try to publish and run
echo Publishing standalone...
dotnet publish MouseMasterClone.csproj -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true /p:PublishReadyToRun=true /p:IncludeNativeLibrariesForSelfExtract=true /p:PublishTrimmed=false
if errorlevel 1 (
    echo Publish failed.
    pause
    exit /b 1
)

if exist "%EXE%" (
    "%EXE%"
) else (
    echo Executable not found after publish.
    pause
)
