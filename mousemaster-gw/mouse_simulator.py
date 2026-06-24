"""
Mouse simulator for GNOME Wayland.

Uses AT-SPI2 (D-Bus accessibility bus) for mouse click simulation,
and the standard XDG Desktop Portal / Wayland interfaces for cursor
movement.

On GNOME Wayland, AT-SPI2's DeviceEventController is the officially
supported mechanism for input injection from assistive technologies.
"""

import struct
from typing import Optional

# ---- AT-SPI2 D-Bus interface constants ----
ATSPI_DBUS_NAME = 'org.a11y.atspi.Registry'
ATSPI_DBUS_PATH = '/org/a11y/atspi/registry/device/eventcontroller'
ATSPI_DBUS_IFACE = 'org.a11y.atspi.DeviceEventController'

# Mouse button constants
BUTTON_LEFT = 1
BUTTON_MIDDLE = 2
BUTTON_RIGHT = 3
BUTTON_SCROLL_UP = 4
BUTTON_SCROLL_DOWN = 5


class MouseSimulator:
    """Simulates mouse input via AT-SPI2 DeviceEventController.

    This works on GNOME Wayland without needing X11 or uinput.
    The accessibility bus must be running (it always is on GNOME).
    """

    def __init__(self, bus: Optional = None):
        """
        Args:
            bus: An optional dbus-python Bus object. If None, connects to
                 the session bus on first use.
        """
        self._bus = bus
        self._controller = None  # lazy init
        self._connected = False

    def _ensure_connected(self):
        """Lazy-initialise D-Bus connection to AT-SPI2 registry."""
        if self._connected:
            return
        try:
            import dbus
            if self._bus is None:
                self._bus = dbus.SessionBus()
            registry_obj = self._bus.get_object(
                ATSPI_DBUS_NAME,
                ATSPI_DBUS_PATH
            )
            self._controller = dbus.Interface(
                registry_obj, ATSPI_DBUS_IFACE
            )
            self._connected = True
        except ImportError:
            raise RuntimeError(
                "The 'dbus' Python module is required. "
                "On GNOME it is usually provided by python-dbus or python3-dbus."
            )
        except dbus.DBusException as e:
            raise RuntimeError(
                "Cannot connect to AT-SPI2 accessibility bus. "
                "Make sure the at-spi2-registryd daemon is running. "
                f"Error: {e}"
            )

    def move_relative(self, dx: int, dy: int):
        """Move cursor by relative offset (pixels)."""
        # AT-SPI2 DeviceEventController supports relative mouse motion
        # via NotifyListeners. However, for actual cursor movement we
        # use the accessibility bus to inject a motion event.
        self._ensure_connected()
        # Generate a mouse motion event relative to current position
        self._controller.NotifyListeners(
            # event_type: 5 = mouse motion
            5,
            # x, y: we set 0,0 and use x/y_delta
            0, 0,
            # button: 0 for motion
            0,
            # event_state: modifiers (0 = none)
            0,
            # x_delta, y_delta: the relative motion
            dx, dy,
            # timestamp
            0,
            # source_window (unused)
            0
        )

    def move_absolute(self, x: int, y: int):
        """Move cursor to absolute screen position (pixels).

        This works by moving to the target in one jump via a motion
        event with large deltas.  For pixel-perfect positioning we
        follow the approach used by the original mousemaster:
        use D-Bus to request the remote cursor position change.
        """
        # AT-SPI2's NotifyListeners with absolute coordinates is
        # unreliable on older GNOME.  We use a two-step approach:
        # 1. Get current position (from the registry)
        # 2. Compute delta and emit relative motion
        cur_x, cur_y = self.get_position()
        dx = x - cur_x
        dy = y - cur_y
        if dx != 0 or dy != 0:
            self.move_relative(dx, dy)

    def get_position(self):
        """Return (x, y) of the current cursor position.

        Queries the AT-SPI2 registry for the pointer location.
        """
        self._ensure_connected()
        socket_obj = self._bus.get_object(
            ATSPI_DBUS_NAME,
            '/org/a11y/atspi/registry/socket'
        )
        socket_iface = dbus.Interface(
            socket_obj,
            'org.a11y.atspi.Socket'
        )
        # GetDesktopCoordinateOrigin returns (x, y) of pointer
        origin = socket_iface.GetDesktopCoordinateOrigin()
        return (int(origin[0]), int(origin[1]))

    def _click_button(self, button: int):
        """Press and release a mouse button."""
        self._ensure_connected()
        # Press
        self._controller.NotifyListeners(
            2 if button <= 3 else 6,  # 2=button press, 6=scroll
            0, 0,  # x, y
            button,  # button code
            0,  # event_state
            0, 0,  # x_delta, y_delta
            0,  # timestamp
            0   # source_window
        )
        # tiny delay between press and release
        import time
        time.sleep(0.01)
        # Release
        self._controller.NotifyListeners(
            3 if button <= 3 else 6,  # 3=button release, 6=scroll
            0, 0,
            button,
            0,
            0, 0,
            0,
            0
        )

    def click_left(self):
        self._click_button(BUTTON_LEFT)

    def click_right(self):
        self._click_button(BUTTON_RIGHT)

    def click_middle(self):
        self._click_button(BUTTON_MIDDLE)

    def scroll(self, delta: int):
        """Scroll vertically. Positive delta = scroll up."""
        self._ensure_connected()
        button = BUTTON_SCROLL_UP if delta > 0 else BUTTON_SCROLL_DOWN
        self._click_button(button)


# --- Standalone simple test ---
if __name__ == '__main__':
    sim = MouseSimulator()
    print(f"Current cursor position: {sim.get_position()}")
    print("Clicking left button (test)")
    sim.click_left()