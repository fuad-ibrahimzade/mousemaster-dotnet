"""
Grid system for mouse position selection.

Implements the 4x4 grid navigation: a screen area is divided into 16
cells labeled A-P.  The user can zoom into a cell (nested refinement)
or make a final selection to move the cursor.

Coordinates are in screen-space pixels.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

GRID_COLS = 4
GRID_ROWS = 4
CELL_LABELS = [chr(ord('A') + i) for i in range(16)]  # A through P


@dataclass
class GridCell:
    """A single cell in the grid."""
    label: str  # A-P
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom) exclusive bottom-right
    center: Tuple[int, int] = field(init=False)

    def __post_init__(self):
        left, top, right, bottom = self.rect
        self.center = (left + (right - left) // 2, top + (bottom - top) // 2)

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]

    @property
    def x(self) -> int:
        return self.rect[0]

    @property
    def y(self) -> int:
        return self.rect[1]

    def contains(self, px: int, py: int) -> bool:
        left, top, right, bottom = self.rect
        return left <= px < right and top <= py < bottom


class GridLevel:
    """A single level of the grid hierarchy.

    Each level divides its area into 16 cells and maps labels to cells.
    """

    def __init__(self, area: Tuple[int, int, int, int]):
        """
        Args:
            area: (left, top, width, height) of the grid area in screen pixels.
        """
        self.area_left, self.area_top, self.area_width, self.area_height = area
        self._cells: List[GridCell] = []
        self._label_map: dict[str, GridCell] = {}
        self._build()

    @property
    def cells(self) -> List[GridCell]:
        return self._cells

    @property
    def label_map(self) -> dict[str, GridCell]:
        return self._label_map

    def _build(self):
        """Divide the area into a 4x4 grid of cells."""
        self._cells.clear()
        self._label_map.clear()

        cell_w = self.area_width // GRID_COLS
        cell_h = self.area_height // GRID_ROWS

        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                idx = r * GRID_COLS + c
                if idx >= len(CELL_LABELS):
                    break
                label = CELL_LABELS[idx]
                left = self.area_left + c * cell_w
                top = self.area_top + r * cell_h
                if c == GRID_COLS - 1:
                    right = self.area_left + self.area_width
                else:
                    right = left + cell_w
                if r == GRID_ROWS - 1:
                    bottom = self.area_top + self.area_height
                else:
                    bottom = top + cell_h

                cell = GridCell(label=label, rect=(left, top, right, bottom))
                self._cells.append(cell)
                self._label_map[label] = cell

    def get_cell(self, label: str) -> Optional[GridCell]:
        """Get a cell by its letter label (A-P). Case-insensitive."""
        return self._label_map.get(label.upper())

    def get_cell_containing(self, px: int, py: int) -> Optional[GridCell]:
        """Find the cell that contains screen point (px, py)."""
        for cell in self._cells:
            if cell.contains(px, py):
                return cell
        return None


class GridState:
    """Manages the grid navigation state machine.

    Tracks the stack of grid levels, allowing zoom-in (nested refinement)
    and zoom-out (back to parent level).  The root level spans the screen
    area of the monitor where the cursor currently is.
    """

    def __init__(self, area: Tuple[int, int, int, int]):
        """
        Args:
            area: (left, top, width, height) of the initial root grid area.
        """
        self._stack: List[GridLevel] = []
        self._push_level(area)

    @property
    def current_level(self) -> Optional[GridLevel]:
        """The current (topmost) grid level."""
        if self._stack:
            return self._stack[-1]
        return None

    @property
    def depth(self) -> int:
        """How many levels deep we are (1 = root-level grid)."""
        return len(self._stack)

    def _push_level(self, area):
        """Push a new grid level for the given area."""
        level = GridLevel(area)
        self._stack.append(level)
        logger.debug("Grid level %d: area=%s", len(self._stack), area)

    def zoom_in(self, label: str) -> Optional[GridCell]:
        """Zoom into a cell by its label.

        Pushes a new grid level covering the area of the selected cell.
        Returns the cell that was zoomed into, or None if invalid.
        """
        level = self.current_level
        if level is None:
            return None
        cell = level.get_cell(label)
        if cell is None:
            return None
        # New area = the cell's rectangle
        new_area = (cell.x, cell.y, cell.width, cell.height)
        self._push_level(new_area)
        return cell

    def zoom_out(self) -> bool:
        """Go up one level (back to parent grid).

        Returns True if we went up, False if already at root.
        """
        if len(self._stack) <= 1:
            return False
        self._stack.pop()
        logger.debug("Zoomed out to grid level %d", len(self._stack))
        return True

    def select_cell(self, label: str) -> Optional[GridCell]:
        """Select a cell in the current grid level.

        If this is the root level, it zooms in (nested refinement).
        If already zoomed in, it returns the cell for final cursor move.

        Returns:
            The cell if this is a final selection (depth >= 2), or None
            if this was a zoom-in (depth was 1).
        """
        level = self.current_level
        if level is None:
            return None
        cell = level.get_cell(label)
        if cell is None:
            return None

        if self.depth == 1:
            # Root level -> zoom in
            self.zoom_in(label)
            return None  # Not final
        else:
            # Already zoomed in -> final selection
            return cell

    def reset(self, new_area: Tuple[int, int, int, int]):
        """Reset the grid back to the root level with a new area."""
        self._stack.clear()
        self._push_level(new_area)