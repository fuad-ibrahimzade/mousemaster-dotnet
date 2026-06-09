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
        // Cover primary screen
        Bounds = Screen.PrimaryScreen.Bounds;
        BackColor = Color.Lime;
        TransparencyKey = Color.Lime; // Makes the background fully transparent
        DoubleBuffered = true;
    }

    protected override bool ShowWithoutActivation => true;
}

public class GridOverlay : OverlayForm
{
    private List<Rectangle> cellRects = new();
    private Dictionary<char, Rectangle> charToRect = new();
    private Rectangle currentArea;

    public event EventHandler<char>? CellSelected;

    public GridOverlay()
    {
        currentArea = Bounds;
        BuildLevel();
    }

    private void BuildLevel()
    {
        charToRect.Clear();
        int cols = 4; // 4x4 grid
        int rows = 4;
        int cellWidth = currentArea.Width / cols;
        int cellHeight = currentArea.Height / rows;
        cellRects = new List<Rectangle>();

        char currentChar = 'A';
        for (int r = 0; r < rows; r++)
        {
            for (int c = 0; c < cols; c++)
            {
                Rectangle rect = new Rectangle(
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
        using var brush = new SolidBrush(Color.FromArgb(128, Color.Black));
        foreach (var rect in cellRects)
        {
            g.FillRectangle(brush, rect);
            g.DrawRectangle(Pens.Yellow, rect);
        }
        // Draw labels
        using var font = new Font("Arial", 24, FontStyle.Bold);
        using var textBrush = new SolidBrush(Color.Yellow);
        char currentChar = 'A';
        foreach (var rect in cellRects)
        {
            if (currentChar > 'Z') break;
            var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center };
            g.DrawString(currentChar.ToString(), font, textBrush, rect, sf);
            currentChar++;
        }
    }

    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {
        // Not used; handled via global hook
        return base.ProcessCmdKey(ref msg, keyData);
    }

    public void SelectCell(char c)
    {
        c = char.ToUpper(c);
        if (charToRect.TryGetValue(c, out Rectangle rect))
        {
            CellSelected?.Invoke(this, c);
        }
    }

    public bool TryGetCellRect(char c, out Rectangle rect)
    {
        return charToRect.TryGetValue(char.ToUpper(c), out rect);
    }
}
