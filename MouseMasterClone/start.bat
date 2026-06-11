@echo off
setlocal
cd /d "%~dp0"

set "SC_EXE=bin\Release\net10.0-windows\win-x64\publish\MouseMasterClone.exe"
set "FD_EXE=bin\Release\net10.0-windows\MouseMasterClone.dll"

if exist "%SC_EXE%" (
    echo [READY] Found standalone executable.
    echo Starting MouseMasterClone...
    "%SC_EXE%"
    exit /b 0
)

if exist "%FD_EXE%" (
    echo [READY] Found framework-dependent build.
    echo Starting MouseMasterClone (requires .NET 10 runtime)...
    dotnet run --project MouseMasterClone.csproj
    exit /b 0
)

echo [INFO] No published executable found.
echo [INFO] Building standalone for the first time - this may take 10-20 seconds.
echo.
call publish_standalone.bat
if errorlevel 1 (
    echo [ERROR] Publish failed.
    pause
    exit /b 1
)

echo [SUCCESS] Build complete.
if exist "%SC_EXE%" (
    echo Starting MouseMasterClone...
    "%SC_EXE%"
) else (
    echo [ERROR] Executable still not found.
    pause
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
