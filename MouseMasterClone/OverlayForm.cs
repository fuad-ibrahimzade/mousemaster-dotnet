using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;

namespace MouseMasterClone;

public class OverlayForm : Form
{
    // Window styles
    private const int WS_EX_TRANSPARENT = 0x20;
    private const int WS_EX_TOPMOST = 0x00000008;
    private const int WS_EX_TOOLWINDOW = 0x80;
    private const int WS_EX_NOACTIVATE = 0x08000000;
    private const int WS_EX_LAYERED = 0x80000;

    protected override CreateParams CreateParams
    {
        get
        {
            var cp = base.CreateParams;
            cp.ExStyle |= WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED;
            return cp;
        }
    }

    public OverlayForm()
    {
        ShowInTaskbar = false;
        FormBorderStyle = FormBorderStyle.None;
        TopMost = true;
        StartPosition = FormStartPosition.Manual;
        BackColor = Color.Magenta;
        TransparencyKey = Color.Magenta;
        DoubleBuffered = true;
    }

    protected override bool ShowWithoutActivation => true;
}

public class GridOverlay : OverlayForm
{
    private readonly Stack<Rectangle> areaStack = new();
    private readonly List<Rectangle> cellRects = new();
    private readonly Dictionary<char, Rectangle> charToRect = new();

    public event EventHandler<char>? CellSelected;

    public GridOverlay()
    {
        // Do not reset here; Bounds not set yet
    }

    public void Reset()
    {
        areaStack.Clear();
        areaStack.Push(Bounds);
        Rebuild();
    }

    public void SelectCell(char c)
    {
        c = char.ToUpper(c);
        if (!charToRect.TryGetValue(c, out Rectangle rect))
            return;

        if (areaStack.Count == 1)
        {
            // Refine to the selected cell (nested level)
            areaStack.Push(rect);
            Rebuild();
        }
        else
        {
            // Final selection: move cursor and notify context
            CellSelected?.Invoke(this, c);
        }
    }

    public bool TryGoUp()
    {
        if (areaStack.Count > 1)
        {
            areaStack.Pop();
            Rebuild();
            return true;
        }
        return false;
    }

    public bool TryGetCellRect(char c, out Rectangle rect)
    {
        return charToRect.TryGetValue(char.ToUpper(c), out rect);
    }

    private void Rebuild()
    {
        BuildLevel();
        Invalidate();
    }

    private void BuildLevel()
    {
        charToRect.Clear();
        cellRects.Clear();
        Rectangle currentArea = areaStack.Peek();
        int cols = 4;
        int rows = 4;
        int cellWidth = currentArea.Width / cols;
        int cellHeight = currentArea.Height / rows;

        char currentChar = 'A';
        for (int r = 0; r < rows; r++)
        {
            for (int c = 0; c < cols; c++)
            {
                var rect = new Rectangle(
                    currentArea.X + c * cellWidth,
                    currentArea.Y + r * cellHeight,
                    cellWidth,
                    cellHeight);
                cellRects.Add(rect);
                if (currentChar <= 'Z')
                {
                    charToRect[currentChar] = rect;
                    currentChar++;
                }
            }
        }
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        // Form's location in screen coordinates
        Point formLocation = this.Location;
        // Draw only letters, transparent background
        using var font = new Font("Arial", 36, FontStyle.Bold);
        using var textBrush = new SolidBrush(Color.FromArgb(230, Color.White));
        foreach (var kvp in charToRect)
        {
            var screenRect = kvp.Value;
            // Convert screen coordinates to client coordinates
            var clientRect = new Rectangle(
                screenRect.X - formLocation.X,
                screenRect.Y - formLocation.Y,
                screenRect.Width,
                screenRect.Height);
            var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center };
            // Draw black outline for readability
            using var outlinePen = new Pen(Color.Black, 3);
            g.DrawString(kvp.Key.ToString(), font, outlinePen.Brush, clientRect, sf);
            g.DrawString(kvp.Key.ToString(), font, textBrush, clientRect, sf);
        }
    }

    protected override bool ShowWithoutActivation => true;
}
