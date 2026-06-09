using System.Drawing;
using System.Windows.Forms;

namespace MouseMasterClone;

public class IndicatorForm : Form
{
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

    public IndicatorForm()
    {
        FormBorderStyle = FormBorderStyle.None;
        ShowInTaskbar = false;
        TopMost = true;
        StartPosition = FormStartPosition.Manual;
        Size = new Size(32, 32);
        // Use magenta as transparent key
        BackColor = Color.Magenta;
        TransparencyKey = Color.Magenta;
        DoubleBuffered = true;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        int size = 8; // half-length from center
        int cx = Width / 2;
        int cy = Height / 2;
        using var pen = new Pen(Color.Red, 2);
        g.DrawLine(pen, cx - size, cy, cx + size, cy);
        g.DrawLine(pen, cx, cy - size, cx, cy + size);
    }

    protected override bool ShowWithoutActivation => true;
}
