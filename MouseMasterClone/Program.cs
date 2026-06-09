using System;
using System.Windows.Forms;

namespace MouseMasterClone;

static class Program
{
    [STAThread]
    static void Main()
    {
        try
        {
            Application.SetHighDpiMode(HighDpiMode.SystemAware);
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            // Add a hidden notify icon to confirm app is running and allow exit
            var icon = new NotifyIcon
            {
                Icon = SystemIcons.Application,
                Visible = true,
                Text = "MouseMasterClone - Running (P or Ctrl+C to quit)"
            };
            var ctx = new ContextMenuStrip();
            ctx.Items.Add("Exit", null, (s, e) => Application.Exit());
            icon.ContextMenuStrip = ctx;
            Application.ApplicationExit += (s, e) => icon.Visible = false;
            Application.Run(new MouseMasterContext());
        }
        catch (Exception ex)
        {
            MessageBox.Show($"MouseMasterClone failed to start:\n\n{ex}", "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            throw;
        }
    }
}