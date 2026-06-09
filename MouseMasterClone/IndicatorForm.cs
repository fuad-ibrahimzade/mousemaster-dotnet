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
        // Transparent background
        BackColor = Color.Magenta;
        TransparencyKey = Color.Magenta;
        DoubleBuffered = true;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        var g = e.Graphics;
        int cx = Width / 2;
        int cy = Height / 2;
        // Outer red circle
        using var redBrush = new SolidBrush(Color.FromArgb(230, Color.Red));
        g.FillEllipse(redBrush, cx - 10, cy - 10, 20, 20);
        // White ring
        using var whitePen = new Pen(Color.White, 2);
        g.DrawEllipse(whitePen, cx - 10, cy - 10, 20, 20);
        // Center dot
        using var centerBrush = new SolidBrush(Color.White);
        g.FillEllipse(centerBrush, cx - 2, cy - 2, 4, 4);
    }

    protected override bool ShowWithoutActivation => true;
}
