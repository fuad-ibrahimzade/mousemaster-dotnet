using System;
using System.Collections.Generic;
using System.Threading;
using System.Windows.Forms;

namespace MouseMasterClone;

public class MouseMasterContext : ApplicationContext
{
    private GlobalKeyboardHook hook;
    private readonly HashSet<int> pressedKeys = new();
    private bool active = false;
    private IndicatorForm? indicator;
    private GridOverlay? gridOverlay;
    private readonly System.Windows.Forms.Timer updateTimer;
    private readonly SynchronizationContext uiContext;
    private const int UpdateInterval = 10; // ms
    private const double MoveSpeed = 10.0; // pixels per update

    // Virtual key codes (hex)
    private readonly HashSet<int> activationKeys = new() { 0xA4, 0x45 }; // LAlt + E
    private const int DeactivationQ = 0x51; // Q
    private const int QuitKeyP = 0x50; // P
    private const int QuitComboLCtrl = 0xA2; // Left Control for Ctrl+C combo
    private const int QuitComboC = 0x43; // C for Ctrl+C combo
    private const int HintGridKey = 0x47; // G
    private const int MoveUpKey = 0x26; // Up Arrow
    private const int MoveDownKey = 0x28; // Down Arrow
    private const int MoveLeftKey = 0x25; // Left Arrow
    private const int MoveRightKey = 0x27; // Right Arrow
    private const int ClickLeftKey = 0xBA; // VK_OEM_1 (;)
    private const int ClickRightKey = 0xDE; // VK_OEM_7 (')
    private const int ClickMiddleKey = 0xA1; // RShift (VK_RSHIFT)
    private const int VK_LSHIFT = 0xA0; // LShift for speed
    private const int VK_RCONTROL = 0xA3; // RControl for speed
    private const int EscapeKey = 0x1B; // Escape

    // Combined set of keys to block when active (grid not visible)
    private readonly HashSet<int> activeModeHandledKeys;

    // Click state
    private bool leftClickPressed = false;
    private bool rightClickPressed = false;
    private bool middleClickPressed = false;

    private bool exiting = false;

    public MouseMasterContext()
    {
        uiContext = SynchronizationContext.Current ?? new SynchronizationContext();

        // Build set of keys to block during active mouse mode
        activeModeHandledKeys = new HashSet<int>
        {
            MoveUpKey, MoveDownKey, MoveLeftKey, MoveRightKey,
            ClickLeftKey, ClickRightKey, ClickMiddleKey,
            // Also block the keys used for activation (LAlt, E) to prevent them from reaching the app
            0xA4, 0x45,
            // Block modifiers for quit and speed
            0xA2, // LControl
            VK_LSHIFT,
            VK_RCONTROL
        };

        indicator = new IndicatorForm();
        indicator.Hide();

        gridOverlay = new GridOverlay();
        gridOverlay.CellSelected += GridOverlay_CellSelected;
        gridOverlay.Hide();

        hook = new GlobalKeyboardHook();
        hook.KeyEvent += OnKeyEvent;
        hook.Hook();

        updateTimer = new System.Windows.Forms.Timer();
        updateTimer.Interval = UpdateInterval;
        updateTimer.Tick += (s, e) => Update();
        updateTimer.Start();
    }

    private void OnKeyEvent(object? sender, KeyboardHookEventArgs e)
    {
        bool shouldHandle = false;
        lock (pressedKeys)
        {
            if (e.IsKeyDown)
            {
                bool isNewPress = !pressedKeys.Contains(e.VirtualKey);
                if (isNewPress)
                    pressedKeys.Add(e.VirtualKey);

                // Check for quit conditions (always, even inactive)
                if (!exiting)
                {
                    bool quit = false;
                    if (isNewPress && e.VirtualKey == QuitKeyP)
                        quit = true;
                    else if (pressedKeys.Contains(QuitComboLCtrl) && pressedKeys.Contains(QuitComboC))
                        quit = true;

                    if (quit)
                    {
                        shouldHandle = true;
                        exiting = true;
                        uiContext.Post(_ =>
                        {
                            try { Dispose(); }
                            catch { }
                            ExitThread();
                        }, null);
                    }
                }

                // Activation: LAlt + E
                if (!active && activationKeys.SetEquals(pressedKeys))
                {
                    shouldHandle = true;
                    uiContext.Post(_ =>
                    {
                        if (!active)
                            Activate();
                    }, null);
                }

                // Deactivation: Q (on initial press)
                if (active && isNewPress && e.VirtualKey == DeactivationQ)
                {
                    shouldHandle = true;
                    uiContext.Post(_ =>
                    {
                        if (active)
                            Deactivate();
                    }, null);
                }

                // Grid toggle: G (on initial press)
                if (active && isNewPress && e.VirtualKey == HintGridKey)
                {
                    shouldHandle = true;
                    uiContext.Post(_ => ToggleGrid(), null);
                }

                if (active)
                {
                    if (gridOverlay.Visible)
                    {
                        // Grid selection/refinement mode
                        if (e.VirtualKey >= (int)Keys.A && e.VirtualKey <= (int)Keys.Z && isNewPress)
                        {
                            char c = (char)e.VirtualKey;
                            shouldHandle = true;
                            uiContext.Post(_ => gridOverlay.SelectCell(c), null);
                        }
                        else if (e.VirtualKey == EscapeKey && isNewPress)
                        {
                            shouldHandle = true;
                            uiContext.Post(_ =>
                            {
                                if (gridOverlay != null && !gridOverlay.TryGoUp())
                                {
                                    ToggleGrid(false);
                                }
                            }, null);
                        }
                        else
                        {
                            // Block all other keys while grid is visible
                            shouldHandle = true;
                        }
                    }
                    else
                    {
                        // Mouse mode: block keys that we use for movement or clicks
                        if (activeModeHandledKeys.Contains(e.VirtualKey))
                            shouldHandle = true;
                    }
                }
            }
            else // key up
            {
                int vk = e.VirtualKey;
                pressedKeys.Remove(vk);
                if (vk == ClickLeftKey) leftClickPressed = false;
                else if (vk == ClickRightKey) rightClickPressed = false;
                else if (vk == ClickMiddleKey) middleClickPressed = false;
            }
        }
        if (shouldHandle)
            e.Handled = true;
    }

    private void Activate()
    {
        if (active) return;
        active = true;
        indicator?.Show();
        indicator?.BringToFront();
        indicator?.Invalidate();
        UpdateIndicatorPosition(); // Set position immediately
    }

    private void Deactivate()
    {
        if (!active) return;
        active = false;
        indicator?.Hide();
        if (gridOverlay?.Visible == true)
            ToggleGrid(false);
        leftClickPressed = rightClickPressed = middleClickPressed = false;
    }

    private void ToggleGrid()
    {
        ToggleGrid(!(gridOverlay?.Visible ?? false));
    }

    private void ToggleGrid(bool show)
    {
        if (show)
        {
            // Determine which screen the cursor is currently on
            var cursorPos = MouseSimulator.GetPosition();
            var screen = Screen.FromPoint(new Point(cursorPos.X, cursorPos.Y));
            gridOverlay.Bounds = screen.Bounds;
            gridOverlay.Reset();
            gridOverlay.Show();
            gridOverlay.BringToFront();
        }
        else
        {
            gridOverlay?.Hide();
        }
    }

    private void GridOverlay_CellSelected(object? sender, char c)
    {
        if (gridOverlay != null && gridOverlay.TryGetCellRect(c, out Rectangle rect))
        {
            int targetX = rect.Left + rect.Width / 2;
            int targetY = rect.Top + rect.Height / 2;
            MouseSimulator.MoveAbsolute(targetX, targetY);
        }
        ToggleGrid(false);
    }

    private void UpdateIndicatorPosition()
    {
        if (indicator != null)
        {
            var pos = MouseSimulator.GetPosition();
            indicator.Location = new Point(pos.X - indicator.Width / 2, pos.Y - indicator.Height / 2);
            indicator.Invalidate(); // Force repaint (ensures visibility)
        }
    }

    private void Update()
    {
        if (!active) return;
        if (gridOverlay != null && gridOverlay.Visible) return;

        lock (pressedKeys)
        {
            // Speed modifiers: Shift = 2x, Ctrl = 0.5x
            bool shift = pressedKeys.Contains(VK_LSHIFT) || pressedKeys.Contains(ClickMiddleKey);
            bool ctrl = pressedKeys.Contains(QuitComboLCtrl) || pressedKeys.Contains(VK_RCONTROL);
            double factor = 1.0;
            if (shift) factor *= 2.0;
            if (ctrl) factor *= 0.5;
            double speed = MoveSpeed * factor;

            int dx = 0, dy = 0;
            if (pressedKeys.Contains(MoveLeftKey)) dx -= (int)speed;
            if (pressedKeys.Contains(MoveRightKey)) dx += (int)speed;
            if (pressedKeys.Contains(MoveUpKey)) dy -= (int)speed;
            if (pressedKeys.Contains(MoveDownKey)) dy += (int)speed;
            if (dx != 0 || dy != 0)
                MouseSimulator.Move(dx, dy);

            if (pressedKeys.Contains(ClickLeftKey) && !leftClickPressed)
            {
                MouseSimulator.ClickLeft();
                leftClickPressed = true;
            }
            if (pressedKeys.Contains(ClickRightKey) && !rightClickPressed)
            {
                MouseSimulator.ClickRight();
                rightClickPressed = true;
            }
            if (pressedKeys.Contains(ClickMiddleKey) && !middleClickPressed)
            {
                MouseSimulator.ClickMiddle();
                middleClickPressed = true;
            }
        }

        // Update cursor indicator position (even if grid is visible)
        UpdateIndicatorPosition();
    }

    protected override void Dispose(bool disposing)
    {
        if (disposing)
        {
            updateTimer?.Stop();
            updateTimer?.Dispose();
            hook?.Dispose();
            indicator?.Dispose();
            gridOverlay?.Dispose();
        }
        base.Dispose(disposing);
    }
}
