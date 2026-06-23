# app.py
import os
import sys
import time
import ctypes
import threading
import winsound
import pyperclip
from pynput import keyboard

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

import config
from audio import AudioRecorder
from transcriber import transcribe_audio
from voice_ui import HoveringRibbon

# Virtual Key Code Mapping for common keys
VK_MAP = {
    'ctrl': 0x11,
    'shift': 0x10,
    'alt': 0x12,
    'win': 0x5B,
    'enter': 0x0D,
    'space': 0x20,
    'backspace': 0x08,
    'tab': 0x09,
    'escape': 0x1B,
    'caps_lock': 0x14,
    'capslock': 0x14,
    'delete': 0x2E,
    'insert': 0x2D,
    'home': 0x24,
    'end': 0x23,
    'pageup': 0x21,
    'pagedown': 0x22,
    'up': 0x26,
    'down': 0x28,
    'left': 0x25,
    'right': 0x27,
    'num_lock': 0x90,
    'scroll_lock': 0x91,
    'print_screen': 0x2C,
    'pause': 0x13,
    'menu': 0x5D,
    # Symbol / punctuation keys
    ';': 0xBA, '=': 0xBB, ',': 0xBC, '-': 0xBD, '.': 0xBE,
    '/': 0xBF, '`': 0xC0, '[': 0xDB, '\\': 0xDC, ']': 0xDD, "'": 0xDE,
}

# Add standard alphanumeric keys
for i in range(26):
    char = chr(ord('a') + i)
    VK_MAP[char] = 0x41 + i # VK_A = 65, etc.
for i in range(10):
    VK_MAP[str(i)] = 0x30 + i # VK_0 = 48, etc.
# Add F1-F24 keys
for i in range(24):
    VK_MAP[f'f{i+1}'] = 0x70 + i # VK_F1 = 112, etc.


def parse_hotkey(hotkey_str):
    """
    Parses a hotkey string (e.g. 'ctrl+shift+d') into a tuple:
    (primary_vk_code, list_of_modifier_vk_codes)
    """
    parts = [p.strip().lower() for p in hotkey_str.split('+')]
    if not parts or parts[0] == '':
        return None, []
        
    primary = parts[-1]
    modifiers = parts[:-1]
    
    primary_vk = VK_MAP.get(primary)
    modifier_vks = [VK_MAP.get(m) for m in modifiers if VK_MAP.get(m) is not None]
    
    return primary_vk, modifier_vks

class AppSignals(QObject):
    """Signals for thread-safe UI updates in PyQt6."""
    start_recording = pyqtSignal()
    stop_recording = pyqtSignal()
    cancel_recording = pyqtSignal()
    update_status = pyqtSignal(str, str) # status, message
    update_volume = pyqtSignal(float)

class VoiceTypistApp(QObject):
    def __init__(self):
        super().__init__()
        # 1. Load configuration
        self.app_config = config.load_config()
        
        # 2. Setup paths
        self.temp_dir = os.path.expanduser("~/.voice_typing_app")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.wav_path = os.path.join(self.temp_dir, "recording.wav")
        
        # 3. Initialize components
        self.recorder = AudioRecorder(filename=self.wav_path)
        self.keyboard_controller = keyboard.Controller()
        
        # 4. Set state variables
        self.recording_active = False
        self.transcribing_active = False
        self.suppress_primary_start_up = False
        self.target_hwnd = None
        
        # 5. Parse initial hotkeys
        self.reload_hotkeys()
        
        # 6. Initialize thread signals
        self.signals = AppSignals()
        self.signals.start_recording.connect(self.start_recording)
        self.signals.stop_recording.connect(self.stop_recording)
        self.signals.cancel_recording.connect(self.cancel_recording)
        self.signals.update_status.connect(self.update_status_gui)
        
        # Apply startup shortcut state based on config
        self.manage_startup_shortcut(self.app_config.get("run_on_startup", False))
        
        # 7. Initialize UI (Hovering Ribbon)
        self.ribbon = HoveringRibbon(
            current_config=self.app_config,
            save_config_callback=self.handle_settings_save,
            on_record_click=self.handle_record_button_click,
            on_stop_click=self.handle_stop_button_click,
            on_exit_callback=self.cleanup
        )
        self.ribbon.show()
        
        # 8. Start volume level polling timer
        self.volume_timer = QTimer()
        self.volume_timer.timeout.connect(self.poll_volume)
        self.volume_timer.start(30) # ~33 FPS
        
        # 9. Start global keyboard hook
        self.listener = keyboard.Listener(win32_event_filter=self._keyboard_event_filter)
        self.listener.start()

    def reload_hotkeys(self):
        """Parse hotkey settings into virtual key codes."""
        start_str = self.app_config.get("start_hotkey", "ctrl+shift+d")
        stop_str = self.app_config.get("stop_hotkey", "enter")
        
        self.start_primary, self.start_modifiers = parse_hotkey(start_str)
        self.stop_primary, self.stop_modifiers = parse_hotkey(stop_str)
        
        print(f"Loaded Hotkeys - Start: {start_str} (VK: {self.start_primary}, Mods: {self.start_modifiers})")
        print(f"Loaded Hotkeys - Stop: {stop_str} (VK: {self.stop_primary}, Mods: {self.stop_modifiers})")

    def handle_settings_save(self, new_config):
        """Callback when user saves new configuration."""
        old_startup = self.app_config.get("run_on_startup", False)
        new_startup = new_config.get("run_on_startup", False)
        self.app_config = new_config
        if config.save_config(new_config):
            self.reload_hotkeys()
            if old_startup != new_startup:
                self.manage_startup_shortcut(new_startup)
            return True
        return False

    def poll_volume(self):
        """Poll the volume level from AudioRecorder and update visualizer."""
        if self.recording_active:
            vol = self.recorder.get_volume()
            self.ribbon.update_volume(vol)

    def _is_pressed(self, vk):
        """Check if a key is globally pressed on the system."""
        return (ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000) != 0

    def _keyboard_event_filter(self, msg, data):
        """
        Win32 event hook filter. Runs on the keyboard hook thread.
        Emits signals to execute recording state updates on the main Qt thread.
        """
        vk = data.vkCode
        is_down = (msg == 256 or msg == 260)
        is_up = (msg == 257 or msg == 261)
        
        # 1. Handle Cancel Recording (Escape key)
        if self.recording_active and vk == 0x1B: # VK_ESCAPE
            if is_down:
                self.signals.cancel_recording.emit()
            return False # Suppress key down and up
            
        # 2. Handle Stop Recording (Stop hotkey)
        if self.recording_active and vk == self.stop_primary:
            mods_pressed = all(self._is_pressed(m) for m in self.stop_modifiers)
            if mods_pressed:
                if is_down:
                    self.signals.stop_recording.emit()
                return False # Suppress key down and up
                
        # 2. Handle Start Recording (Start hotkey)
        if not self.recording_active and not self.transcribing_active and vk == self.start_primary:
            mods_pressed = all(self._is_pressed(m) for m in self.start_modifiers)
            if mods_pressed:
                if is_down:
                    self.suppress_primary_start_up = True
                    self.signals.start_recording.emit()
                return False # Suppress key down
                
        # Suppress the release event of the start hotkey to prevent junk character inputs
        if vk == self.start_primary and is_up:
            if self.suppress_primary_start_up:
                self.suppress_primary_start_up = False
                return False # Suppress key up
                
        return True

    def play_beep(self, type_name):
        """Play feedback sound indicators (soft click clicks)."""
        if not self.app_config.get("sound_effects", True):
            return
        try:
            if type_name == "start":
                winsound.Beep(2000, 20) # Soft tick
            elif type_name == "stop":
                winsound.Beep(1400, 20) # Soft tack
            elif type_name == "success":
                winsound.Beep(2000, 15)
                time.sleep(0.04)
                winsound.Beep(2200, 15) # Double tick
            elif type_name == "error":
                winsound.Beep(250, 150) # Soft low buzz
        except Exception as e:
            print(f"Beep error: {e}")

    def handle_record_button_click(self):
        """Handle clicks on the record button (toggles start or cancel)."""
        if self.recording_active:
            # Cancel recording if clicked while active
            self.cancel_recording()
        elif not self.transcribing_active:
            self.start_recording()

    def handle_stop_button_click(self):
        """Handle clicks on the stop button (stops and transcribes)."""
        if self.recording_active:
            self.stop_recording()

    def start_recording(self):
        """Start audio recording (called on main thread)."""
        if self.recording_active:
            return
            
        # Capture current active window where the user wants to type
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        ribbon_hwnd = int(self.ribbon.winId()) if hasattr(self, 'ribbon') else 0
        if hwnd != ribbon_hwnd:
            self.target_hwnd = hwnd
            print(f"Captured target window HWND: {self.target_hwnd}")
            
        print("Starting recording...")
        self.play_beep("start")
        
        if self.recorder.start():
            self.recording_active = True
            self.ribbon.update_status("Recording")
        else:
            print("Failed to start recording.")
            self.play_beep("error")
            self.ribbon.update_status("Error", "Mic start failed")

    def cancel_recording(self):
        """Cancel and discard the current recording."""
        if not self.recording_active:
            return
            
        print("Canceling recording...")
        self.play_beep("stop")
        self.recording_active = False
        self.recorder.stop()
        self.ribbon.update_status("Idle")
        
        # Clean up temp file
        if os.path.exists(self.wav_path):
            try:
                os.remove(self.wav_path)
            except Exception:
                pass

    def stop_recording(self):
        """Stop audio recording and trigger transcription (called on main thread)."""
        if not self.recording_active:
            return
            
        print("Stopping recording...")
        self.play_beep("stop")
        self.recording_active = False
        self.ribbon.update_status("Transcribing")
        self.transcribing_active = True
        
        file_path = self.recorder.stop()
        if file_path:
            # Transcribe in a background worker thread to keep the Qt GUI responsive
            threading.Thread(target=self.process_transcription, args=(file_path,), daemon=True).start()
        else:
            print("No audio file recorded.")
            self.transcribing_active = False
            self.play_beep("error")
            self.ribbon.update_status("Error", "No audio captured")

    def process_transcription(self, filepath):
        """Background transcription task."""
        try:
            api_key = self.app_config.get("api_key", "").strip()
            if not api_key:
                raise ValueError("API Key is missing")
                
            text = transcribe_audio(api_key, filepath)
            print(f"Transcribed Text: {text}")
            
            if text and text.strip():
                # Perform the paste
                self.paste_text(text)
                self.play_beep("success")
                self.signals.update_status.emit("Idle", "")
            else:
                print("Transcription was empty.")
                self.play_beep("error")
                self.signals.update_status.emit("Error", "Empty transcript")
                
        except Exception as e:
            print(f"Transcription process error: {e}")
            self.play_beep("error")
            self.signals.update_status.emit("Error", str(e)[:30])
        finally:
            self.transcribing_active = False
            # Clean up temp file
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass

    def update_status_gui(self, status, message):
        """Helper slot to update the ribbon status safely on the main thread."""
        self.ribbon.update_status(status, message)

    def paste_text(self, text):
        """Paste text at cursor using clipboard manipulation."""
        # Restore focus to the target window if we have one
        if hasattr(self, 'target_hwnd') and self.target_hwnd:
            print(f"Restoring focus to window HWND: {self.target_hwnd}")
            # ONLY call ShowWindow if the window is minimized (iconic). 
            # Calling ShowWindow on a maximized window — even SW_SHOW — causes it to shrink.
            # So we skip ShowWindow entirely for non-minimized windows and only steal focus.
            if ctypes.windll.user32.IsIconic(self.target_hwnd):
                # SW_RESTORE (9): brings a minimized window back to normal
                ctypes.windll.user32.ShowWindow(self.target_hwnd, 9)
            # Do NOT call ShowWindow for maximized/normal windows - it will shrink them
            ctypes.windll.user32.SetForegroundWindow(self.target_hwnd)
            time.sleep(0.15) # Wait for OS window focus transition
            
        try:
            original_clipboard = pyperclip.paste()
        except Exception:
            original_clipboard = ""
            
        try:
            pyperclip.copy(text)
            time.sleep(0.15) # Wait for OS clipboard update
            
            # Win32 virtual key codes
            VK_CONTROL = 0x11
            VK_SHIFT = 0x10
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002
            
            # Force release control and shift first to clear physical stuck states
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)
            
            # Press Ctrl
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            time.sleep(0.01)
            
            # Press V
            ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)
            time.sleep(0.03)
            
            # Release V
            ctypes.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)
            
            # Release Ctrl
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.02)
            
            # Double check modifier release
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
            ctypes.windll.user32.keybd_event(VK_SHIFT, 0, KEYEVENTF_KEYUP, 0)
                
            # Allow the application a dynamic moment to process the paste.
            # Longer text requires more time for the target application to read from clipboard.
            # We scale the sleep time: 0.6s minimum, up to 2.5s for very long paragraphs.
            dynamic_sleep = max(0.6, min(2.5, len(text) / 300.0))
            time.sleep(dynamic_sleep)
        finally:
            # Restore original clipboard
            if original_clipboard is not None:
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass

    def cleanup(self):
        """Cleanup resources on app exit."""
        print("Cleaning up resources...")
        if self.recording_active:
            self.recorder.stop()
        if self.listener:
            self.listener.stop()
        if os.path.exists(self.wav_path):
            try:
                os.remove(self.wav_path)
            except Exception:
                pass
        os._exit(0)

    def manage_startup_shortcut(self, enabled):
        """Creates or removes shortcut in Windows Startup directory."""
        try:
            startup_dir = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs\Startup")
            shortcut_path = os.path.join(startup_dir, "VoiceTypist.lnk")
            
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
            else:
                exe_path = os.path.abspath(sys.argv[0])
                
            if enabled:
                if not os.path.exists(shortcut_path):
                    ps_cmd = f"$s = (New-Object -ComObject WScript.Shell).CreateShortcut('{shortcut_path}'); $s.TargetPath = '{exe_path}'; $s.WorkingDirectory = '{os.path.dirname(exe_path)}'; $s.Save()"
                    os.system(f'powershell -WindowStyle Hidden -Command "{ps_cmd}"')
                    print("Created Windows startup shortcut.")
            else:
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)
                    print("Removed Windows startup shortcut.")
        except Exception as e:
            print(f"Error managing startup shortcut: {e}")

if __name__ == "__main__":
    app_qt = QApplication(sys.argv)
    app = VoiceTypistApp()
    sys.exit(app_qt.exec())
