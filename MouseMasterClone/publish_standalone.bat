@echo off
setlocal
cd /d "%~dp0"
echo Publishing standalone (self-contained) for win-x64...
dotnet publish MouseMasterClone.csproj -c Release -r win-x64 --self-contained true ^
    /p:PublishSingleFile=true ^
    /p:PublishReadyToRun=true ^
    /p:IncludeNativeLibrariesForSelfExtract=true ^
    /p:PublishTrimmed=false
if errorlevel 1 (
    echo Publish failed.
    pause
    exit /b 1
)
echo Published to bin\Release\net10.0-windows\win-x64\publish\
pause
