"""
Main application state machine for mousemaster-gw.

Manages activation states, keyboard dispatch, mouse movement,
click actions, and grid navigation.

Mirrors the logic of MouseMasterContext.cs but adapted for GNOME Wayland.
"""

from __future__ import annotations
import logging
import threading
from typing import Optional

from grid import GridCell
from overlay_indicator import IndicatorOverlay, ScreenInfo
from overlay_grid import GridOverlayWindow

logger = logging.getLogger(__name__)

# ---- Constants ----
MOVE_SPEED = 10.0  # pixels per tick
MOVE_INTERVAL_MS = 10  # timer tick interval
KEY_REPEAT_THRESHOLD_MS = 300  # initial delay before key repeat

# Activation combo: 56 (Left Alt) + 18 (E)
ACTIVATION_KEYS = {56, 18}  # KEY_LEFTALT, KEY_E
DEACTIVATION_KEY = 16  # Q
QUIT_KEY = 25  # P
GRID_KEY = 34  # G
ESC_KEY = 1  # KEY_ESC

MOVE_UP = 103
MOVE_DOWN = 108
MOVE_LEFT = 105
MOVE_RIGHT = 106
CLICK_LEFT = 39  # KEY_SEMICOLON
CLICK_RIGHT = 40  # KEY_APOSTROPHE
CLICK_MIDDLE = 54  # KEY_RIGHTSHIFT
MOD_SHIFT = 42  # KEY_LEFTSHIFT
MOD_CTRL = 29  # KEY_LEFTCTRL

# Key codes for letter grid selection (A-Z: 30-56, but A=30, P=...)
# We handle any A-Z key while grid is visible
KEY_A = 30
KEY_Z = 56  # Actually Z is 44, but cap at 56 for safety

# ---- Key repeat / held key tracking ----
HELD_MOVE_KEYS = {MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT}


class MouseMasterApp:
    """Main application state machine.

    Integrates the uinput device, AT-SPI2 listener, indicator overlay,
    and grid overlay.  Runs a GLib main loop for event dispatch.
    """

    def __init__(self, uinput_device, atspi_listener, mainloop):
        """
        Args:
            uinput_device: UInputDevice instance for mouse/keyboard injection.
            atspi_listener: ATSPIListener instance for global key events.
            mainloop: The GLib.MainLoop to quit on exit.
        """
        self._uinput = uinput_device
        self._listener = atspi_listener
        self._mainloop = mainloop
        self._indicator = IndicatorOverlay()
        self._grid_overlay = GridOverlayWindow()

        # Thread safety for _pressed_keys (accessed from D-Bus thread)
        self._lock = threading.Lock()

        # State
        self._active = False
        self._pressed_keys: set[int] = set()

        # Click repeat prevention
        self._left_click_down = False
        self._right_click_down = False
        self._middle_click_down = False

        # Exit flag
        self._exiting = False

        # GLib timeout source IDs
        self._move_timer_source = None
        self._indicator_timer_source = None

    # ---- Initialization ----

    def init(self):
        """Create windows and overlays."""
        self._indicator.create()
        self._grid_overlay.create()

    # ---- Main event loop (called from GLib) ----

    def on_key_event(self, key_code: int, is_press: bool, modifiers: int):
        """Process a keyboard event from AT-SPI2 listener.

        This is called from the D-Bus event thread, so we need to be
        careful about thread safety. We modify state atomically.
        """
        handled = self._handle_key_event(key_code, is_press)
        return handled

    def _handle_key_event(self, key_code: int, is_press: bool) -> bool:
        """Internal key event handler. Returns True if event was consumed."""

        # Track pressed keys (thread-safe)
        with self._lock:
            if is_press:
                self._pressed_keys.add(key_code)
            else:
                self._pressed_keys.discard(key_code)

            active = self._active
            pressed = set(self._pressed_keys)

        # Quit checks (always active, even when inactive)
        if not self._exiting:
            quit_needed = False
            if is_press and key_code == QUIT_KEY:  # P
                quit_needed = True
            elif (pressed & {29, 97}) and key_code == 46:
                # Ctrl (left or right) + C
                if is_press and key_code == 46:  # KEY_C
                    quit_needed = True

            if quit_needed:
                self._exiting = True
                logger.info("Quit requested")
                GLib.idle_add(self._quit)
                return True

        # Activation: LAlt + E
        if not active and ACTIVATION_KEYS.issubset(pressed):
            if is_press and key_code in ACTIVATION_KEYS:
                GLib.idle_add(self._activate)
                return True

        # Deactivation: Q
        if active and is_press and key_code == DEACTIVATION_KEY:
            GLib.idle_add(self._deactivate)
            return True

        # Grid toggle
        if active and is_press and key_code == GRID_KEY:
            GLib.idle_add(self._toggle_grid)
            return True

        # Handle active-mode keys
        if active:
            if self._grid_overlay.is_visible():
                # Grid mode
                return self._handle_grid_key(key_code, is_press)
            else:
                # Mouse mode
                return self._handle_mouse_key(key_code, is_press)

        return False  # Not handled (pass through)

    def _handle_grid_key(self, key_code: int, is_press: bool) -> bool:
        """Handle key events while grid is visible."""
        if not is_press:
            return True  # Block all key releases in grid mode

        # A-Z keys for cell selection
        if KEY_A <= key_code <= KEY_Z:
            label = chr(ord('A') + (key_code - KEY_A))
            GLib.idle_add(self._on_grid_cell_selected, label)
            return True

        # Escape: go up one level or close grid
        if key_code == ESC_KEY:
            GLib.idle_add(self._on_grid_escape)
            return True

        # Block all other keys while grid is visible
        return True

    def _handle_mouse_key(self, key_code: int, is_press: bool) -> bool:
        """Handle key events in mouse movement mode."""
        # Movement keys are handled by timer, not individually.
        # Just block them so they don't reach applications.
        handled_keys = {
            MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT,
            CLICK_LEFT, CLICK_RIGHT, CLICK_MIDDLE,
            MOD_SHIFT, MOD_CTRL,
            # Activation keys (prevent them reaching apps)
        } | ACTIVATION_KEYS | {DEACTIVATION_KEY, GRID_KEY}

        if key_code in handled_keys:
            return True
        return False

    # ---- Event callbacks (run on main thread via idle_add) ----

    def _activate(self):
        """Activate mouse master mode."""
        if self._active:
            return
        self._active = True

        # Show indicator
        self._update_indicator_position()
        self._indicator.show()

        # Start move timer
        GLib.source_remove(self._move_timer_source)
        self._move_timer_source = GLib.timeout_add(
            MOVE_INTERVAL_MS, self._on_move_tick
        )

        # Start indicator position update timer
        GLib.source_remove(self._indicator_timer_source)
        self._indicator_timer_source = GLib.timeout_add(
            MOVE_INTERVAL_MS, self._on_indicator_tick
        )

        logger.info("Activated")

    def _deactivate(self):
        """Deactivate mouse master mode."""
        if not self._active:
            return
        self._active = False

        self._indicator.hide()
        if self._grid_overlay.is_visible():
            self._grid_overlay.hide()

        # Stop timers
        if self._move_timer_source:
            GLib.source_remove(self._move_timer_source)
            self._move_timer_source = None
        if self._indicator_timer_source:
            GLib.source_remove(self._indicator_timer_source)
            self._indicator_timer_source = None

        # Reset click states
        self._left_click_down = False
        self._right_click_down = False
        self._middle_click_down = False

        logger.info("Deactivated")

    def _quit(self):
        """Shutdown the application."""
        self._deactivate()
        self._indicator.destroy()
        self._grid_overlay.destroy()
        self._listener.stop()
        self._uinput.close()
        self._mainloop.quit()
        logger.info("Application quit")

    def _toggle_grid(self):
        """Toggle the grid overlay on/off."""
        if self._grid_overlay.is_visible():
            self._grid_overlay.hide()
        else:
            # Get the monitor where the cursor is
            px, py = self._get_pointer_position()
            mon = ScreenInfo.get_monitor_at(px, py)
            self._grid_overlay.show_grid(mon)

    def _on_grid_cell_selected(self, label: str):
        """Handle a grid cell selection key (A-P)."""
        cell = self._grid_overlay.handle_cell_select(label)
        if cell is not None:
            # Final selection: move cursor and close grid
            target_x, target_y = cell.center
            self._uinput.move_absolute(target_x, target_y)
            self._grid_overlay.hide()

    def _on_grid_escape(self):
        """Handle Escape key in grid mode."""
        if not self._grid_overlay.go_up():
            # Already at root level, close grid
            self._grid_overlay.hide()

    def _get_pointer_position(self):
        """Get current cursor position from AT-SPI2."""
        return self._listener.get_pointer_position()

    # ---- Timer ticks ----

    def _on_move_tick(self) -> bool:
        """Timer callback for continuous mouse movement and clicks."""
        with self._lock:
            if not self._active:
                return False
            keys = set(self._pressed_keys)

        # Speed modifiers
        shift = (MOD_SHIFT in keys)
        ctrl = (MOD_CTRL in keys)
        factor = 1.0
        if shift:
            factor *= 2.0
        if ctrl:
            factor *= 0.5
        speed = int(MOVE_SPEED * factor)

        # Movement
        dx, dy = 0, 0
        if MOVE_LEFT in keys:
            dx -= speed
        if MOVE_RIGHT in keys:
            dx += speed
        if MOVE_UP in keys:
            dy -= speed
        if MOVE_DOWN in keys:
            dy += speed
        if dx != 0 or dy != 0:
            self._uinput.move_relative(dx, dy)

        # Clicks (single shot, not held)
        if CLICK_LEFT in keys and not self._left_click_down:
            self._uinput.click_left()
            self._left_click_down = True
        elif CLICK_LEFT not in keys:
            self._left_click_down = False

        if CLICK_RIGHT in keys and not self._right_click_down:
            self._uinput.click_right()
            self._right_click_down = True
        elif CLICK_RIGHT not in keys:
            self._right_click_down = False

        if CLICK_MIDDLE in keys and not self._middle_click_down:
            self._uinput.click_middle()
            self._middle_click_down = True
        elif CLICK_MIDDLE not in keys:
            self._middle_click_down = False

        return True  # Keep timer running

    def _on_indicator_tick(self) -> bool:
        """Timer callback to update indicator position."""
        if not self._active:
            return False
        self._update_indicator_position()
        return True

    def _update_indicator_position(self):
        """Move indicator to current cursor position."""
        px, py = self._get_pointer_position()
        self._indicator.move_to(px, py)