"""
GTK3 overlay indicator window.

Shows a red dot at the cursor position while the mouse master is active.
Uses GTK3's popup/utility window with click-through transparency.

This works on GNOME Wayland because GTK3 properly handles window layers
and transparency on Wayland.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, cairo
    HAS_GTK = True
except ImportError:
    HAS_GTK = False


class IndicatorOverlay:
    """Small red dot indicator that follows the cursor.

    Uses a small GTK window with no decorations, transparent background,
    and always-on-top behavior.
    """

    def __init__(self):
        if not HAS_GTK:
            raise RuntimeError("GTK3 (PyGObject) is required")
        self._window = None

    def create(self):
        """Create the indicator window (hidden by default)."""
        if self._window is not None:
            return
        self._window = Gtk.Window.new(Gtk.WindowType.POPUP)
        self._window.set_title("mousemaster-gw-indicator")
        self._window.set_default_size(32, 32)
        self._window.set_resizable(False)
        self._window.set_decorated(False)
        self._window.set_keep_above(True)
        self._window.set_skip_taskbar_hint(True)
        self._window.set_skip_pager_hint(True)
        self._window.set_app_paintable(True)
        self._window.set_accept_focus(False)

        # Transparent background
        screen = self._window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self._window.set_visual(visual)

        # Make click-through via input shape
        self._window.realize()
        self._window.set_opacity(1.0)

        # Drawing
        self._window.connect("draw", self._on_draw)

        # Initially hidden
        self._window.hide()

    def _on_draw(self, widget, cr: cairo.Context):
        """Draw the red dot indicator."""
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()

        # Clear with transparent
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        # Red circle
        cx = width / 2
        cy = height / 2
        radius = 10

        # Outer red fill
        cr.set_source_rgba(1.0, 0.0, 0.0, 0.9)
        cr.arc(cx, cy, radius, 0, 2 * 3.14159)
        cr.fill()

        # White ring
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.8)
        cr.set_line_width(2.0)
        cr.arc(cx, cy, radius - 1, 0, 2 * 3.14159)
        cr.stroke()

        # Center dot
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)
        cr.arc(cx, cy, 2, 0, 2 * 3.14159)
        cr.fill()

    def show(self):
        """Show the indicator window."""
        if self._window:
            self._window.show_all()

    def hide(self):
        """Hide the indicator window."""
        if self._window:
            self._window.hide()

    def move_to(self, x: int, y: int):
        """Move the indicator window centered at (x, y)."""
        if self._window:
            w = self._window.get_allocated_width()
            h = self._window.get_allocated_height()
            self._window.move(x - w // 2, y - h // 2)

    def destroy(self):
        """Destroy the indicator window."""
        if self._window:
            self._window.destroy()
            self._window = None


class ScreenInfo:
    """Utility to query screen/monitor information via GDK."""

    @staticmethod
    def get_monitors():
        """Return a list of monitor geometries.

        Each entry: (x, y, width, height) in screen coordinates.
        """
        display = Gdk.Display.get_default()
        if display is None:
            return [(0, 0, 1920, 1080)]  # fallback

        monitors = []
        for i in range(display.get_n_monitors()):
            monitor = display.get_monitor(i)
            geo = monitor.get_geometry()
            scale = monitor.get_scale_factor()
            monitors.append((
                geo.x * scale,
                geo.y * scale,
                geo.width * scale,
                geo.height * scale,
            ))
        return monitors

    @staticmethod
    def get_primary_monitor():
        """Return (x, y, width, height) of the primary monitor."""
        display = Gdk.Display.get_default()
        if display is None:
            return (0, 0, 1920, 1080)
        monitor = display.get_primary_monitor()
        if monitor is None:
            monitor = display.get_monitor(0)
        geo = monitor.get_geometry()
        scale = monitor.get_scale_factor()
        return (
            geo.x * scale,
            geo.y * scale,
            geo.width * scale,
            geo.height * scale,
        )

    @staticmethod
    def get_monitor_at(x: int, y: int):
        """Return (x, y, width, height) of the monitor containing (x, y)."""
        display = Gdk.Display.get_default()
        if display is None:
            return (0, 0, 1920, 1080)
        mon = display.get_monitor_at_point(x, y)
        if mon is None:
            mon = display.get_primary_monitor()
        if mon is None:
            mon = display.get_monitor(0)
        geo = mon.get_geometry()
        scale = mon.get_scale_factor()
        return (
            geo.x * scale,
            geo.y * scale,
            geo.width * scale,
            geo.height * scale,
        )

    @staticmethod
    def get_monitor_scale():
        """Return the UI scale factor for the primary monitor."""
        display = Gdk.Display.get_default()
        if display is None:
            return 1.0
        mon = display.get_primary_monitor()
        if mon is None:
            mon = display.get_monitor(0)
        return mon.get_scale_factor()