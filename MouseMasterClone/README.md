# MouseMasterClone

A lightweight, keyboard-driven mouse control tool for Windows, inspired by [mousemaster](https://github.com/petoncle/mousemaster). Control your mouse cursor, perform clicks, and navigate using only the keyboard—no administrator privileges required.

## Features

- **Continuous mouse movement**: Move cursor with Arrow Keys (Up, Down, Left, Right)
- **Activation combo**: `Left Alt + E` to activate; `Q` to deactivate; `P` or `Ctrl+C` to quit
- **Mouse clicks**: `;` (left), `'` (right), `RShift` (middle)
- **Grid navigation**: Press `G` to show a 4x4 grid labeled A‑P over the current area. Press a letter to zoom into that cell and show a sub‑grid. Press another letter to move the cursor to that cell (final). `Esc` goes back one level (or closes grid at root).
- **Cursor indicator**: Red dot appears at cursor when active, disappears when deactivated.
- **Non-intrusive overlay**: Transparent windows that don't steal focus
- **Portable**: Single executable, no installation, no admin rights needed

## Requirements

- Windows 10 or later
- **Standalone build**: no .NET runtime required (included)
- **Framework-dependent**: .NET 10.0 Desktop Runtime (Windows)
  - Download from: https://dotnet.microsoft.com/download/dotnet/10.0
  - Select "ASP.NET Core Runtime" or "Desktop Runtime" for Windows x64

## Quick Start

1. Ensure .NET 8.0 Desktop Runtime is installed:
   ```
   dotnet --info
   ```
   Look for `Microsoft.WindowsDesktop.App` in the runtimes list.

2. Build the project (first time only):
   ```
   build.bat
   ```
   Or manually:
   ```
   dotnet build MouseMasterClone
   ```

3. Run the application:
   ```
   start.bat
   ```
   Or directly:
   ```
   dotnet run --project MouseMasterClone
   ```

## Usage

### Activation

- Press `Left Alt + E` to **activate** mouse control.
- Press `Q` or `P` to **deactivate** and hide overlays.

### While Active

- **Move cursor**: Arrow Keys (↑ ↓ ← →)
  - Hold `Shift` for **2× faster** movement
  - Hold `Ctrl` for **½× slower** movement
  - Hold both for normal speed
- **Left click**: `;`
- **Right click**: `'` (apostrophe/quote)
- **Middle click**: `Right Shift`
- **Grid navigation**:
  1. Press `G` to show a 4x4 grid labeled A-P over the whole screen.
  2. Press a letter to zoom into that cell (sub‑grid appears).
  3. Press another letter to move the cursor to that final cell and close the grid.
  4. `Esc` goes back one level (or closes the grid if at the root level).

### Notes

- The **indicator** (red dot) appears centered on the cursor when active.
- Overlays are **click-through** and **non-activating**; they won't interfere with normal app usage.
- Global keyboard hook intercepts used keys to prevent them from reaching other applications.

## Project Structure

```
MouseMasterClone/
├── GlobalKeyboardHook.cs   # Low-level Windows keyboard hook
├── MouseSimulator.cs       # SendInput-based mouse/keyboard simulation
├── OverlayForm.cs          # Transparent grid overlay form
├── IndicatorForm.cs        # Active indicator window
├── MouseMasterContext.cs   # Main application logic
├── Program.cs              # Entry point
├── MouseMasterClone.csproj
├── build.bat               # Build script
├── start.bat               # Run script
└── README.md               # This file
```

## Troubleshooting

### Build fails with "NETSDK1085" or similar

- Ensure you have the **Windows Desktop** workload for .NET 8.0:
  ```
  dotnet workload install microsoft-net-sdk-windows
  ```

### Application doesn't start

- Check that .NET 8.0 Desktop Runtime is installed.
- Try running `dotnet run --project MouseMasterClone` from the command line to see error messages.

### Keyboard shortcuts don't work

- Run as Administrator **only if** you encounter permission issues (should not be necessary).
- Some applications (e.g., games, elevated apps) may require elevated privileges to control; however, this tool is designed to work without admin rights for standard desktop usage.

### Cursor movement is too slow/fast

- Edit `MouseMasterContext.cs` line 17: change `moveSpeed` value.

## Building from Source

```
dotnet restore
dotnet build MouseMasterClone -c Release
```

The executable will be at:
```
MouseMasterClone/bin/Release/net8.0-windows/MouseMasterClone.exe
```

You can copy `MouseMasterClone.exe` and any `.dll` files from that directory to a folder and run it standalone (requires .NET runtime installed).

## Design Notes

- Uses [SetWindowsHookEx](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-setwindowshookexw) for a global keyboard hook.
- Uses [SendInput](https://learn.microsoft.com/windows/win32/api/winuser/nf-winuser-sendinput) for mouse movement and clicks.
- Overlay windows use WS_EX_TRANSPARENT, WS_EX_NOACTIVATE, and WS_EX_LAYERED for click-through transparency.
- Built with .NET 8.0 Windows Forms targeting `net8.0-windows`.

## License

Educational clone. Original mousemaster by petoncle licensed under GPLv3.
