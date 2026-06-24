"""
AT-SPI2-based global keyboard listener for GNOME Wayland.

Uses the org.a11y.atspi.DeviceEventController D-Bus interface to
register for global keyboard events.  This is the standard Wayland-
compatible approach to receive keyboard input without X11.

On GNOME, the at-spi2-registryd daemon is always running when the
accessibility bus is enabled (it is by default in modern GNOME).
"""

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

ATSPI_DBUS_NAME = "org.a11y.atspi.Registry"
ATSPI_DBUS_PATH = "/org/a11y/atspi/registry/device/eventcontroller"
ATSPI_DBUS_IFACE = "org.a11y.atspi.DeviceEventController"

# Event types
EVENT_KEY_PRESS = 1
EVENT_KEY_RELEASE = 2
EVENT_MOUSE_PRESS = 3
EVENT_MOUSE_RELEASE = 4
EVENT_MOUSE_MOTION = 5

# Keyboard modifier masks
MODIFIER_SHIFT = 1 << 0
MODIFIER_CTRL = 1 << 2
MODIFIER_ALT = 1 << 3
MODIFIER_META = 1 << 4


class ATSPIListener:
    """Listens for global keyboard events via AT-SPI2 on GNOME Wayland.

    Provides a callback-based interface for receiving key press/release
    events from anywhere on the desktop.
    """

    def __init__(
        self,
        on_key_event: Optional[Callable] = None,
    ):
        """
        Args:
            on_key_event: Callable(key_code, is_press) invoked when
                          a keyboard event is received.
        """
        self._on_key_event = on_key_event
        self._bus = None
        self._controller = None
        self._running = False
        self._thread = None
        self._mainloop = None

        # Cache for pointer position (updated on mouse events)
        self._pointer_x = 0
        self._pointer_y = 0

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self):
        """Start listening for global keyboard events.

        Runs a GLib main loop in a background thread.  Keyboard events
        are dispatched to the registered callback.
        """
        if self._running:
            return

        try:
            import dbus
            import dbus.mainloop.glib
            from gi.repository import GLib
        except ImportError as e:
            raise RuntimeError(
                "Required Python modules not found. On GNOME, install:\n"
                "  - python-dbus (or python3-dbus)\n"
                f"  - pygobject (or python3-gi)\n"
                f"Missing: {e}"
            )

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self._bus = dbus.SessionBus()
        registry_obj = self._bus.get_object(ATSPI_DBUS_NAME, ATSPI_DBUS_PATH)
        self._controller = dbus.Interface(
            registry_obj, ATSPI_DBUS_IFACE
        )

        # Register for all keyboard events
        # RegisterDeviceEventListener(event_type, filter_string, callback)
        keyboard_filter = (
            "type='keyboard',layout='qwerty',keycode='*'"
        )
        self._controller.RegisterDeviceEventListener(
            EVENT_KEY_PRESS,
            keyboard_filter,
            self._on_dbus_event,
        )
        self._controller.RegisterDeviceEventListener(
            EVENT_KEY_RELEASE,
            keyboard_filter,
            self._on_dbus_event,
        )
        logger.info("AT-SPI2 keyboard listener registered")

        # Also register for mouse motion to track cursor position
        mouse_filter = (
            "type='mouse',pointer='*'"
        )
        self._controller.RegisterDeviceEventListener(
            EVENT_MOUSE_MOTION,
            mouse_filter,
            self._on_dbus_event,
        )

        self._running = True
        self._mainloop = GLib.MainLoop()
        logger.info("AT-SPI2 listener main loop started")
        self._mainloop.run()

    def stop(self):
        """Stop listening and clean up."""
        self._running = False
        if self._mainloop:
            self._mainloop.quit()
            self._mainloop = None
        self._controller = None
        self._bus = None
        logger.info("AT-SPI2 listener stopped")

    def _on_dbus_event(self, event):
        """D-Bus callback for AT-SPI2 device events.

        event is a dbus.Struct containing:
          (type, x, y, button, event_state, x_delta, y_delta, timestamp, source_window)
        For keyboard events:
          x = keycode, y = unused, button = unused, event_state = modifiers
        """
        ev_type = event[0]
        if ev_type == EVENT_KEY_PRESS or ev_type == EVENT_KEY_RELEASE:
            key_code = int(event[1])  # x field = key code
            is_press = ev_type == EVENT_KEY_PRESS
            if self._on_key_event:
                self._on_key_event(key_code, is_press, int(event[4]))
        elif ev_type == EVENT_MOUSE_MOTION:
            # update cached pointer position from absolute coords
            # AT-SPI2 provides screen-relative coordinates in x, y
            self._pointer_x = int(event[1])
            self._pointer_y = int(event[2])

    @staticmethod
    def get_pointer_position():
        """Get the current cursor position via D-Bus.

        Works on Wayland through the AT-SPI2 registry socket.
        Returns (x, y) in screen coordinates.
        """
        try:
            import dbus
            bus = dbus.SessionBus()
            socket_obj = bus.get_object(ATSPI_DBUS_NAME,
                                        "/org/a11y/atspi/registry/socket")
            socket_iface = dbus.Interface(socket_obj,
                                          "org.a11y.atspi.Socket")
            origin = socket_iface.GetDesktopCoordinateOrigin()
            return (int(origin[0]), int(origin[1]))
        except Exception:
            return (0, 0)


# ---- Key code mappings (from linux/input-event-codes.h) ----
# AT-SPI2 uses Linux evdev key codes.

KEY_MAP = {
    # (name, evdev_code)
    "ESC": 1, "KEY_ESC": 1,
    "1": 2, "2": 3, "3": 4, "4": 5, "5": 6,
    "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
    "Q": 16, "W": 17, "E": 18, "R": 19, "T": 20,
    "Y": 21, "U": 22, "I": 23, "O": 24, "P": 25,
    "A": 30, "S": 31, "D": 32, "F": 33, "G": 34,
    "H": 35, "J": 36, "K": 37, "L": 38,
    "SEMICOLON": 39,  # ;
    "APOSTROPHE": 40,  # '
    "GRAVE": 41,  # `
    "BACKSLASH": 43,
    "Z": 44, "X": 45, "C": 46, "V": 47,
    "B": 48, "N": 49, "M": 50,
    "COMMA": 51, "DOT": 52, "SLASH": 53,
    "RIGHTSHIFT": 54,
    "LEFTSHIFT": 42,
    "LEFTCTRL": 29, "RIGHTCTRL": 97,
    "LEFTALT": 56, "RIGHTALT": 100,
    "SPACE": 57,
    "CAPSLOCK": 58,
    "F1": 59, "F2": 60, "F3": 61, "F4": 62,
    "F5": 63, "F6": 64, "F7": 65, "F8": 66,
    "F9": 67, "F10": 68, "F11": 87, "F12": 88,
    "UP": 103, "DOWN": 108, "LEFT": 105, "RIGHT": 106,
    "ENTER": 28, "BACKSPACE": 14, "TAB": 15,
    "DELETE": 111, "INSERT": 110,
    "HOME": 102, "END": 107, "PAGEUP": 104, "PAGEDOWN": 109,
}


def keycode_to_name(code: int) -> str:
    """Convert an evdev key code to a readable name."""
    for name, c in KEY_MAP.items():
        if c == code:
            return name
    return f"KEY_{code}"


def name_to_keycode(name: str) -> Optional[int]:
    """Convert a key name to an evdev key code."""
    return KEY_MAP.get(name.upper())