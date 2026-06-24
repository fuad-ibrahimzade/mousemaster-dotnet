"""
mousemaster-gw — Keyboard-driven mouse controller for GNOME Wayland.

A self-contained keyboard-driven mouse control tool inspired by
mousemaster (https://github.com/petoncle/mousemaster), ported to
GNOME Wayland with zero external dependencies.

Usage:
  python3 mousemaster-gw/main.py

Activation:
  Left Alt + E  — activate mouse mode
  Q             — deactivate
  P  or Ctrl+C  — quit

Features:
  - Arrow keys for mouse movement (Shift=2x, Ctrl=0.5x)
  - ;  (semicolon)  = left click
  - '  (apostrophe)  = right click
  - Right Shift       = middle click
  - G  = toggle 4x4 grid navigation
  - Red dot indicator follows cursor when active

Requirements (pre-installed on all GNOME desktops):
  - Python 3.x
  - PyGObject (gi.repository)
  - python-dbus
  - /dev/uinput (kernel module, user in 'input' group)

Zero pip installs needed. Uses only system libraries.
"""

import argparse
import logging
import os
import signal
import sys


def check_requirements():
    """Verify that all system requirements are met.

    Returns True if OK, False with guidance if not.
    """
    errors = []

    # Check uinput
    if not os.path.exists("/dev/uinput"):
        errors.append(
            "/dev/uinput not found. Load the uinput kernel module:\n"
            "  sudo modprobe uinput"
        )
    else:
        if not os.access("/dev/uinput", os.W_OK):
            errors.append(
                "No write permission on /dev/uinput.\n"
                "Add yourself to the 'input' group:\n"
                "  sudo usermod -aG input $USER\n"
                "Then log out and back in (or reboot)."
            )

    # Check PyGObject
    try:
        from gi.repository import Gtk, GLib, Gdk, cairo  # noqa: F401
    except ImportError:
        errors.append(
            "PyGObject (gi.repository) is not available.\n"
            "On Fedora: sudo dnf install python3-gobject\n"
            "On Ubuntu: sudo apt install python3-gi python3-gi-cairo\n"
            "It is pre-installed on most GNOME desktop systems."
        )

    # Check dbus
    try:
        import dbus  # noqa: F401
    except ImportError:
        errors.append(
            "python-dbus is not available.\n"
            "On Fedora: sudo dnf install python3-dbus\n"
            "On Ubuntu: sudo apt install python3-dbus\n"
            "It is usually pre-installed on GNOME."
        )

    if errors:
        print("=== mousemaster-gw: requirements check failed ===", file=sys.stderr)
        for e in errors:
            print(f"\n  - {e}", file=sys.stderr)
        print(file=sys.stderr)
        return False
    return True


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(
        description="mousemaster-gw — Keyboard-driven mouse for GNOME Wayland"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="Skip requirements check",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    # Check requirements
    if not args.no_check and not check_requirements():
        sys.exit(1)

    print("== mousemaster-gw starting ==")
    print("  Activate: Left Alt + E")
    print("  Deactivate: Q")
    print("  Quit: P or Ctrl+C")
    print("  Grid: G  |  Move: Arrow keys")
    print("  Left click: ;  |  Right click: '  |  Middle click: RShift")
    print()

    # Import implementation modules
    from uinput_mouse import UInputDevice
    from atspi_listener import ATSPIListener
    from app import MouseMasterApp
    from gi.repository import GLib

    # Create virtual uinput device
    uinput = UInputDevice("mousemaster-gw")

    # Create GLib MainLoop
    loop = GLib.MainLoop()

    # Create the app
    app = MouseMasterApp(uinput, None, loop)

    # Create AT-SPI2 listener and connect to app
    def key_event_callback(key_code, is_press, modifiers):
        return app.on_key_event(key_code, is_press, modifiers)

    listener = ATSPIListener(on_key_event=key_event_callback)

    # Store listener reference in app
    app._listener = listener

    # Initialize overlays
    app.init()

    # Start the AT-SPI2 listener in a separate thread
    import threading
    listener_thread = threading.Thread(
        target=listener.start,
        daemon=True,
        name="atspi-listener",
    )
    listener_thread.start()

    # Handle SIGINT (Ctrl+C) gracefully
    def sigint_handler(signum, frame):
        logger.info("Received SIGINT, shutting down...")
        GLib.idle_add(app._quit)

    signal.signal(signal.SIGINT, sigint_handler)

    try:
        logger.info("Entering GLib main loop")
        loop.run()
    except KeyboardInterrupt:
        pass
    finally:
        listener.stop()
        uinput.close()
        logger.info("mousemaster-gw stopped")


if __name__ == "__main__":
    main()