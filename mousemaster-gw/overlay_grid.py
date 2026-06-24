"""
GTK3 grid overlay window.

Displays the 4x4 grid with letter labels (A-P) as a semi-transparent
overlay on top of all windows.  Supports multiple grid levels through
nested refinement.
"""

from __future__ import annotations
import logging
from typing import List, Optional, Tuple

from gi.repository import Gtk, Gdk, GLib, cairo, Pango

from grid import GridState, GridCell, GRID_COLS, GRID_ROWS

logger = logging.getLogger(__name__)


class GridOverlayWindow:
    """A GTK popup window that renders the grid overlay.

    Each cell is drawn with its letter label.  The overlay covers the
    full area of the grid and is click-through, always-on-top, and
    non-activating.
    """

    GRID_ALPHA = 0.15       # Background alpha per cell
    BORDER_COLOR = (0.6, 0.6, 0.6, 0.9)  # cell border
    TEXT_COLOR = (1.0, 1.0, 1.0, 0.9)
    TEXT_OUTLINE_COLOR = (0.0, 0.0, 0.0, 0.7)

    def __init__(self):
        self._window: Optional[Gtk.Window] = None
        self._grid: Optional[GridState] = None
        self._font_size = 36

    def create(self):
        """Create the grid overlay window (hidden by default)."""
        if self._window is not None:
            return

        self._window = Gtk.Window.new(Gtk.WindowType.POPUP)
        self._window.set_title("mousemaster-gw-grid")
        self._window.set_decorated(False)
        self._window.set_keep_above(True)
        self._window.set_skip_taskbar_hint(True)
        self._window.set_skip_pager_hint(True)
        self._window.set_app_paintable(True)
        self._window.set_accept_focus(False)

        # RGBA visual for transparency
        screen = self._window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self._window.set_visual(visual)

        self._window.realize()

        # Connect draw
        self._window.connect("draw", self._on_draw)
        self._window.hide()

    def show_grid(self, area: Tuple[int, int, int, int]):
        """Show the grid overlay covering the given monitor area.

        Args:
            area: (x, y, width, height) of the monitor in screen pixels.
        """
        if self._window is None:
            return

        self._grid = GridState(area)
        left, top, width, height = area
        self._window.move(left, top)
        self._window.resize(width, height)

        # Adjust font size to cell size
        cell_w = width // GRID_COLS
        cell_h = height // GRID_ROWS
        self._font_size = max(12, min(cell_w, cell_h) // 3)

        self._window.show_all()
        self._window.queue_draw()

    def refine_grid(self, cell_label: str):
        """Zoom into the given cell (nested refinement).

        Called when user selects a cell at the root level.
        """
        if self._grid is None:
            return
        cell = self._grid.zoom_in(cell_label)
        if cell is None:
            return

        # Resize overlay to the cell area
        left, top, right, bottom = cell.rect
        width = right - left
        height = bottom - top
        self._window.move(left, top)
        self._window.resize(width, height)

        cell_w = width // GRID_COLS
        cell_h = height // GRID_ROWS
        self._font_size = max(12, min(cell_w, cell_h) // 3)

        self._window.queue_draw()

    def go_up(self) -> bool:
        """Go up one grid level. Returns False if already at root."""
        if self._grid is None:
            return False
        if not self._grid.zoom_out():
            return False

        # Recompute area from current level
        level = self._grid.current_level
        if level is None:
            return False

        # The current grid level area covers the entire visible grid;
        # we need to set the window to the area of the whole grid.
        # Find bounding box of all cells in current level.
        cells = level.cells
        if not cells:
            return False
        left = min(c.x for c in cells)
        top = min(c.y for c in cells)
        right = max(c.x + c.width for c in cells)
        bottom = max(c.y + c.height for c in cells)
        self._window.move(left, top)
        self._window.resize(right - left, bottom - top)

        cell_w = (right - left) // GRID_COLS
        cell_h = (bottom - top) // GRID_ROWS
        self._font_size = max(12, min(cell_w, cell_h) // 3)

        self._window.queue_draw()
        return True

    def try_get_cell(self, label: str) -> Optional[GridCell]:
        """Get the cell for the given label at the current grid level."""
        if self._grid is None:
            return None
        level = self._grid.current_level
        if level is None:
            return None
        return level.get_cell(label)

    def handle_cell_select(self, label: str) -> Optional[GridCell]:
        """Handle a cell selection key press.

        If at root level, refines (zooms in).
        If at nested level, returns the cell for final cursor move.

        Returns:
            The cell to move the cursor to, or None if refinement happened.
        """
        if self._grid is None:
            return None
        cell = self._grid.select_cell(label)
        if cell is None:
            # This was a zoom-in (refinement)
            self._update_from_current_level()
            return None
        return cell

    def _update_from_current_level(self):
        """Resize and reposition the overlay to match the current grid level."""
        if self._grid is None:
            return
        level = self._grid.current_level
        if level is None:
            return

        cells = level.cells
        if not cells:
            return
        left = min(c.x for c in cells)
        top = min(c.y for c in cells)
        right = max(c.x + c.width for c in cells)
        bottom = max(c.y + c.height for c in cells)

        self._window.move(left, top)
        self._window.resize(right - left, bottom - top)

        cell_w = (right - left) // GRID_COLS
        cell_h = (bottom - top) // GRID_ROWS
        self._font_size = max(12, min(cell_w, cell_h) // 3)

        self._window.queue_draw()

    def hide(self):
        """Hide the grid overlay."""
        if self._window:
            self._window.hide()

    def is_visible(self) -> bool:
        return self._window is not None and self._window.get_visible()

    def destroy(self):
        """Destroy the overlay window."""
        if self._window:
            self._window.destroy()
            self._window = None

    def _on_draw(self, widget, cr: cairo.Context):
        """Draw the grid overlay."""
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        left, top = widget.get_position()

        # Clear with transparent
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(cairo.Operator.SOURCE)
        cr.paint()
        cr.set_operator(cairo.Operator.OVER)

        if self._grid is None:
            return

        level = self._grid.current_level
        if level is None:
            return

        cell_w = width // GRID_COLS
        cell_h = height // GRID_ROWS

        # Draw each cell
        for idx, cell in enumerate(level.cells):
            r = idx // GRID_COLS
            c = idx % GRID_COLS
            cx = c * cell_w
            cy = r * cell_h
            cw = cell_w
            ch = cell_h

            # Cell background (very subtle fill)
            cr.set_source_rgba(0.3, 0.3, 0.5, self.GRID_ALPHA)
            cr.rectangle(cx, cy, cw, ch)
            cr.fill()

            # Cell border
            cr.set_source_rgba(*self.BORDER_COLOR)
            cr.set_line_width(1.5)
            cr.rectangle(cx, cy, cw, ch)
            cr.stroke()

            # Draw the letter label
            if cell.label <= 'P':  # only A-P
                # Outline
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
                                    cairo.FONT_WEIGHT_BOLD)
                cr.set_font_size(self._font_size)

                # Get text extents for centering
                x_bearing, y_bearing, tw, th, _, _ = cr.text_extents(cell.label)
                tx = cx + (cw - tw) / 2 - x_bearing
                ty = cy + (ch + th) / 2

                # Text outline
                cr.set_source_rgba(*self.TEXT_OUTLINE_COLOR)
                cr.set_line_width(3)
                cr.move_to(tx, ty)
                cr.text_path(cell.label)
                cr.stroke()

                # Text fill
                cr.set_source_rgba(*self.TEXT_COLOR)
                cr.move_to(tx, ty)
                cr.show_text(cell.label)