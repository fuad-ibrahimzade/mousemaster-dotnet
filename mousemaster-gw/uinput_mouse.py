"""
uinput-based mouse and keyboard injection for GNOME Wayland.

Uses the Linux uinput kernel module (/dev/uinput) to create a virtual
input device that can simulate mouse movement, clicks, and keyboard
presses.  This is the only reliable way to inject input on Wayland
without root or portal grants.

Requirements:
  - CONFIG_INPUT_UINPUT=y in the kernel (always on in desktop distros)
  - Write permission on /dev/uinput (user must be in the 'input' group)
    Run: sudo usermod -aG input $USER && reboot
"""

import ctypes
import ctypes.util
import struct
import time
import os
import errno
import logging

logger = logging.getLogger(__name__)

# ---- Linux input event codes (from linux/input-event-codes.h) ----

# Event types
EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03

# SYN events
SYN_REPORT = 0
SYN_CONFIG = 1

# Relative axes
REL_X = 0x00
REL_Y = 0x01
REL_WHEEL = 0x08
REL_HWHEEL = 0x06

# Absolute axes
ABS_X = 0x00
ABS_Y = 0x01
ABS_MT_SLOT = 0x2f
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36

# Mouse buttons (EV_KEY codes)
BTN_LEFT = 0x110
BTN_RIGHT = 0x111
BTN_MIDDLE = 0x112

# Keyboard keys (subset, EV_KEY codes)
KEY_ESC = 1
KEY_1 = 2
KEY_2 = 3
KEY_3 = 4
KEY_4 = 5
KEY_5 = 6
KEY_6 = 7
KEY_7 = 8
KEY_8 = 9
KEY_9 = 10
KEY_0 = 11
KEY_Q = 16
KEY_W = 17
KEY_E = 18
KEY_R = 19
KEY_T = 20
KEY_Y = 21
KEY_U = 22
KEY_I = 23
KEY_O = 24
KEY_P = 25
KEY_A = 30
KEY_S = 31
KEY_D = 32
KEY_F = 33
KEY_G = 34
KEY_H = 35
KEY_J = 36
KEY_K = 37
KEY_L = 38
KEY_SEMICOLON = 39
KEY_APOSTROPHE = 40
KEY_LEFTALT = 56
KEY_RIGHTSHIFT = 54
KEY_LEFTCTRL = 29
KEY_C = 46
KEY_GRAVE = 41  # backtick/tilde
KEY_SPACE = 57
KEY_LEFT = 105
KEY_RIGHT = 106
KEY_UP = 103
KEY_DOWN = 108
KEY_ENTER = 28
KEY_BACKSPACE = 14
KEY_TAB = 15
KEY_CAPSLOCK = 58
KEY_LEFTSHIFT = 42
KEY_COMPOSE = 127

# ---- uinput ioctl constants ----
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502
UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_SET_RELBIT = 0x40045566
UI_SET_ABSBIT = 0x40045567
UI_SET_MSCBIT = 0x40045568
UI_SET_LEDBIT = 0x40045569
UI_SET_SNDBIT = 0x4004556a
UI_SET_FFBIT = 0x4004556b
UI_SET_PHYS = 0x4004556c
UI_SET_SWBIT = 0x4004556d
UI_SET_PROPBIT = 0x4004556e

# uinput device descriptor struct size
UINPUT_DEVICE_SIZE = 80  # sizeof(struct uinput_user_dev)


class UInputDevice:
    """Virtual input device backed by /dev/uinput.

    Creates a combined mouse + keyboard device that the kernel accepts
    as a legitimate input source.  Mouse movement is sent as relative
    events; absolute positioning uses SetCursorPos-style approach via
    relative motion deltas.
    """

    _fd: int = -1
    _have_abs: bool = False

    def __init__(self, name: str = "mousemaster-gw virtual input"):
        self._name = name
        self._open()

    def _open(self):
        """Open /dev/uinput and configure the virtual device."""
        import fcntl

        # Try common paths
        for path in ("/dev/uinput", "/dev/input/uinput"):
            try:
                self._fd = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
                break
            except PermissionError:
                raise PermissionError(
                    "No write permission on /dev/uinput. "
                    "Add yourself to the 'input' group:\n"
                    "  sudo usermod -aG input $USER\n"
                    "Then log out and back in (or reboot)."
                )
            except FileNotFoundError:
                continue
        else:
            raise RuntimeError(
                "Cannot find /dev/uinput. The uinput kernel module may "
                "not be loaded. Run: sudo modprobe uinput"
            )

        # Enable event types
        ioctl = fcntl.ioctl

        def set_bit(ioctl_req, bit):
            ioctl(self._fd, ioctl_req, bit)

        set_bit(UI_SET_EVBIT, EV_KEY)  # keys and buttons
        set_bit(UI_SET_EVBIT, EV_REL)  # relative axis (mouse movement)
        set_bit(UI_SET_EVBIT, EV_ABS)  # absolute axis (optional)
        set_bit(UI_SET_EVBIT, EV_SYN)  # synchronization

        # Enable relative axes
        set_bit(UI_SET_RELBIT, REL_X)
        set_bit(UI_SET_RELBIT, REL_Y)
        set_bit(UI_SET_RELBIT, REL_WHEEL)
        set_bit(UI_SET_RELBIT, REL_HWHEEL)

        # Enable mouse buttons
        for btn in (BTN_LEFT, BTN_RIGHT, BTN_MIDDLE):
            set_bit(UI_SET_KEYBIT, btn)

        # Enable keyboard keys we use
        keys_to_enable = [
            KEY_LEFTALT, KEY_E, KEY_Q, KEY_P, KEY_G,
            KEY_LEFTCTRL, KEY_C,
            KEY_LEFT, KEY_RIGHT, KEY_UP, KEY_DOWN,
            KEY_SEMICOLON, KEY_APOSTROPHE, KEY_RIGHTSHIFT,
            KEY_LEFTSHIFT,
            KEY_ESC,
        ]
        # Also enable A-Z for grid selection
        keys_to_enable.extend(range(KEY_1, KEY_0 + 1))  # 0-9 as fallback
        for k in range(KEY_A, KEY_Z + 1):
            keys_to_enable.append(k)
        for k in keys_to_enable:
            set_bit(UI_SET_KEYBIT, k)

        # Write the uinput_user_dev struct
        dev_data = bytearray(UINPUT_DEVICE_SIZE)
        name_bytes = self._name.encode("utf-8")
        dev_data[0:len(name_bytes)] = name_bytes
        dev_data[0:80] = dev_data[0:80]  # pad to 80 bytes
        os.write(self._fd, bytes(dev_data))

        # Create the device
        ioctl(self._fd, UI_DEV_CREATE)

        logger.info("uinput virtual device created: %s", self._name)

    def close(self):
        """Destroy the virtual input device."""
        if self._fd >= 0:
            try:
                import fcntl
                fcntl.ioctl(self._fd, UI_DEV_DESTROY)
            except Exception:
                pass
            os.close(self._fd)
            self._fd = -1
            logger.info("uinput virtual device destroyed")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ---- Low-level event writing ----

    def _write_event(self, ev_type: int, code: int, value: int):
        """Write a single input_event struct."""
        # struct input_event {
        #     struct timeval time;  // 8 bytes (sec, usec, both long)
        #     unsigned short type;  // 2 bytes
        #     unsigned short code;  // 2 bytes
        #     unsigned int value;   // 4 bytes
        # };
        # Total: 16 bytes on 32-bit, 24 bytes on 64-bit (timeval is 2 longs)
        # On Linux x86_64: struct timeval is 16 bytes (2 * 8-byte longs)
        # We use struct.pack with proper format
        ts_sec = 0
        ts_usec = 0
        # Use Q (unsigned long long) x2 for timespec, H/H/I for type/code/value
        # struct input_event on x86_64: two __u64 for time, __u16, __u16, __u32
        data = struct.pack("QQHHI", ts_sec, ts_usec, ev_type, code, value)
        os.write(self._fd, data)

    def _syn(self):
        self._write_event(EV_SYN, SYN_REPORT, 0)

    # ---- Mouse control ----

    def move_relative(self, dx: int, dy: int):
        """Move the cursor by (dx, dy) pixels relative to current position."""
        if dx != 0:
            self._write_event(EV_REL, REL_X, dx)
        if dy != 0:
            self._write_event(EV_REL, REL_Y, dy)
        self._syn()

    def move_absolute(self, x: int, y: int):
        """Move the cursor to an absolute screen position.

        On Wayland we cannot warp the cursor, so we compute the delta
        from the current position and use relative movement.  The caller
        must provide a way to get the current cursor position.
        """
        from atspi_listener import ATSPIListener
        cur_x, cur_y = ATSPIListener.get_pointer_position()
        dx = x - cur_x
        dy = y - cur_y
        if dx != 0 or dy != 0:
            self.move_relative(dx, dy)

    def _button(self, btn_code: int, press: bool):
        """Press or release a button."""
        self._write_event(EV_KEY, btn_code, 1 if press else 0)
        self._syn()

    def click_left(self):
        self._button(BTN_LEFT, True)
        time.sleep(0.01)
        self._button(BTN_LEFT, False)

    def click_right(self):
        self._button(BTN_RIGHT, True)
        time.sleep(0.01)
        self._button(BTN_RIGHT, False)

    def click_middle(self):
        self._button(BTN_MIDDLE, True)
        time.sleep(0.01)
        self._button(BTN_MIDDLE, False)

    def scroll(self, delta: int):
        """Scroll vertically. Positive = scroll up (toward user)."""
        amount = 1
        if delta > 0:
            self._write_event(EV_REL, REL_WHEEL, amount)
        else:
            self._write_event(EV_REL, REL_WHEEL, -amount)
        self._syn()

    def press_key(self, key_code: int):
        """Press a keyboard key (generate key down event)."""
        self._write_event(EV_KEY, key_code, 1)
        self._syn()

    def release_key(self, key_code: int):
        """Release a keyboard key (generate key up event)."""
        self._write_event(EV_KEY, key_code, 0)
        self._syn()

    def tap_key(self, key_code: int):
        """Press and release a keyboard key."""
        self.press_key(key_code)
        time.sleep(0.01)
        self.release_key(key_code)