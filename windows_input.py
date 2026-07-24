# windows_input.py
import ctypes
import time
import pyperclip

# Win32 Constants and Structures for SendInput
LONG = ctypes.c_long
DWORD = ctypes.c_ulong
WORD = ctypes.c_ushort
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP       = 0x0002
KEYEVENTF_UNICODE     = 0x0004
KEYEVENTF_SCANCODE    = 0x0008

INPUT_KEYBOARD = 1

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", WORD),
        ("wScan", WORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", LONG),
        ("dy", LONG),
        ("mouseData", DWORD),
        ("dwFlags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", ULONG_PTR)
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", DWORD),
        ("wParamL", WORD),
        ("wParamH", WORD)
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("ki", KEYBDINPUT),
        ("mi", MOUSEINPUT),
        ("hi", HARDWAREINPUT)
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", DWORD),
        ("union", _INPUT_UNION)
    ]

def send_key_event(vk, keyup=False):
    """Sends a single key event using modern Win32 SendInput with hardware scancode."""
    scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    flags = KEYEVENTF_SCANCODE
    if keyup:
        flags |= KEYEVENTF_KEYUP
    if vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2E, 0x2D, 0x5B, 0x5C, 0x5D):
        flags |= KEYEVENTF_EXTENDEDKEY
        
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.wScan = scan
    inp.union.ki.dwFlags = flags
    inp.union.ki.time = 0
    inp.union.ki.dwExtraInfo = 0
    
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

def release_all_modifiers():
    """Forces explicit release of Control, Shift, Alt, and Windows keys to clear OS input table state."""
    modifiers = [0x11, 0x10, 0x12, 0x5B, 0x5C] # VK_CONTROL, VK_SHIFT, VK_MENU, VK_LWIN, VK_RWIN
    for vk in modifiers:
        send_key_event(vk, keyup=True)

def paste_text_via_sendinput(text, target_hwnd=None):
    """Pastes text at cursor using clipboard manipulation and SendInput (Ctrl+V) with complete modifier cleanup."""
    if target_hwnd:
        # Restore window if iconic (minimized), then set foreground focus cleanly without touching window geometry
        if ctypes.windll.user32.IsIconic(target_hwnd):
            ctypes.windll.user32.ShowWindow(target_hwnd, 9) # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(target_hwnd)
        time.sleep(0.12)
        
    # Clear any stuck OS modifier keys prior to pasting
    release_all_modifiers()
    time.sleep(0.02)
    
    try:
        original_clipboard = pyperclip.paste()
    except Exception:
        original_clipboard = ""
        
    try:
        pyperclip.copy(text)
        time.sleep(0.12) # Wait for Windows OS clipboard sync
        
        # Press Ctrl + V via SendInput
        send_key_event(0x11, keyup=False) # VK_CONTROL down
        time.sleep(0.01)
        send_key_event(0x56, keyup=False) # VK_V down
        time.sleep(0.03)
        send_key_event(0x56, keyup=True)  # VK_V up
        time.sleep(0.01)
        send_key_event(0x11, keyup=True)  # VK_CONTROL up
        time.sleep(0.02)
        
        # Release all modifier keys again to leave Windows OS input table 100% clean
        release_all_modifiers()
        
        dynamic_sleep = max(0.5, min(2.0, len(text) / 300.0))
        time.sleep(dynamic_sleep)
    finally:
        # Restore original clipboard content
        if original_clipboard is not None:
            try:
                pyperclip.copy(original_clipboard)
            except Exception:
                pass
