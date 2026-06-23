# ui.py
import sys
import random
import math
import time
from PyQt6.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QLabel, 
    QPushButton, QDialog, QVBoxLayout, QLineEdit, 
    QMessageBox, QGraphicsDropShadowEffect, QMenu,
    QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, QPoint, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QAction, QMouseEvent

# Curated Hex Colors
COLOR_BG = "rgba(26, 27, 38, 225)"         # Translucent deep dark slate
COLOR_BORDER = "rgba(255, 255, 255, 30)"    # Subtle border highlight
COLOR_TEXT = "#CDD6F4"                      # Clean white-grey text
COLOR_IDLE = "#3B82F6"                      # Electric Blue
COLOR_RECORDING = "#EF4444"                 # Vibrant Coral Red
COLOR_TRANSCRIBING = "#F59E0B"              # Amber Yellow
COLOR_ERROR = "#7C3AED"                     # Royal Violet

# Global ToolTip stylesheet styling to resemble Google dialogs/tooltips
GLOBAL_STYLE = """
    QToolTip {
        background-color: #1A1B26;
        color: #CDD6F4;
        border: 1px solid rgba(255, 255, 255, 35);
        border-radius: 6px;
        padding: 6px 10px;
        font-family: "Segoe UI", sans-serif;
        font-size: 9pt;
    }
"""

class WaveformWidget(QWidget):
    """
    A custom widget that draws a dynamic, Siri-like voice wave
    oscillating based on volume levels during recording.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(120, 22)
        self.volume = 0.0
        self.status = "Idle"
        self.heights = [3.0] * 9
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30) # ~33 FPS

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))

    def set_status(self, status):
        self.status = status
        if status != "Recording":
            self.volume = 0.0

    def animate(self):
        for i in range(9):
            if self.status == "Recording":
                boosted_vol = math.sqrt(self.volume)
                target = 3.0 + (boosted_vol * 22.0 * random.uniform(0.6, 1.4))
                target = min(22.0, target)
            elif self.status == "Transcribing":
                import time
                t = time.time() * 8.0
                target = 4.0 + 6.0 * math.sin(t + i * 0.8)
            else:
                target = 3.0 + random.uniform(-0.3, 0.3)
                target = max(2.5, min(4.0, target))
                
            self.heights[i] = self.heights[i] * 0.65 + target * 0.35
            
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        bar_width = 3
        spacing = 4
        total_width = 9 * bar_width + 8 * spacing
        start_x = (width - total_width) // 2
        center_y = height // 2
        
        if self.status == "Recording":
            color = QColor(COLOR_RECORDING)
        elif self.status == "Transcribing":
            color = QColor(COLOR_TRANSCRIBING)
        elif self.status == "Error":
            color = QColor(COLOR_ERROR)
        else:
            color = QColor(100, 116, 139) # Slate grey
            
        for i in range(9):
            bar_height = self.heights[i]
            x = start_x + i * (bar_width + spacing)
            y = center_y - bar_height / 2
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(int(x), int(y), bar_width, int(bar_height), 1.5, 1.5)

class HotkeyLineEdit(QLineEdit):
    """A read-only QLineEdit that captures physical keyboard press combinations."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Click to set hotkey...")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
    def focusInEvent(self, event):
        self.setText("Press key combination...")
        self.setStyleSheet("border: 1px solid #A6E3A1; color: #A6E3A1; font-weight: bold;")
        super().focusInEvent(event)
        
    def focusOutEvent(self, event):
        self.setStyleSheet("")
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        # Ignore standalone modifier presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta,
                   Qt.Key.Key_Super_L, Qt.Key.Key_Super_R):
            return

        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")

        # Full key name mapping
        SPECIAL_KEYS = {
            Qt.Key.Key_Return:      "enter",
            Qt.Key.Key_Enter:       "enter",
            Qt.Key.Key_Space:       "space",
            Qt.Key.Key_Escape:      "escape",
            Qt.Key.Key_Tab:         "tab",
            Qt.Key.Key_Backspace:   "backspace",
            Qt.Key.Key_Delete:      "delete",
            Qt.Key.Key_Insert:      "insert",
            Qt.Key.Key_Home:        "home",
            Qt.Key.Key_End:         "end",
            Qt.Key.Key_PageUp:      "pageup",
            Qt.Key.Key_PageDown:    "pagedown",
            Qt.Key.Key_Up:          "up",
            Qt.Key.Key_Down:        "down",
            Qt.Key.Key_Left:        "left",
            Qt.Key.Key_Right:       "right",
            Qt.Key.Key_CapsLock:    "caps_lock",
            Qt.Key.Key_NumLock:     "num_lock",
            Qt.Key.Key_ScrollLock:  "scroll_lock",
            Qt.Key.Key_Print:       "print_screen",
            Qt.Key.Key_Pause:       "pause",
            Qt.Key.Key_Menu:        "menu",
        }

        if key in SPECIAL_KEYS:
            key_name = SPECIAL_KEYS[key]
        elif Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_name = chr(key).lower()
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            key_name = chr(key)  # '0'-'9'
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F24:
            key_name = f"f{key - Qt.Key.Key_F1 + 1}"
        else:
            # For symbols, punctuation, numpad: use the raw text character
            txt = event.text().strip()
            if txt:
                key_name = txt.lower()
            else:
                # Fallback: use Qt key name stripping the 'Key_' prefix
                raw = str(key).split('.')[-1].replace('Key_', '').lower()
                if raw:
                    key_name = raw
                else:
                    return  # Truly unknown key, ignore

        parts.append(key_name)
        hotkey_str = "+".join(parts)
        self.setText(hotkey_str)
        self.clearFocus()

class SettingsDialog(QDialog):
    """Frameless, translucent glassmorphic settings dialog."""
    def __init__(self, current_config, save_callback, parent=None):
        super().__init__(parent)
        self.current_config = current_config
        self.save_callback = save_callback
        self.drag_position = QPoint()
        self.init_ui()

    def init_ui(self):
        # Frameless, translucent dialog
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(380, 310)
        
        # Dialog central frame layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(6, 6, 6, 6)
        
        # Central styled card container
        self.container = QWidget(self)
        self.container.setObjectName("Card")
        self.container.setStyleSheet(f"""
            QWidget#Card {{
                background-color: {COLOR_BG};
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
            }}
            QLabel {{
                color: #CDD6F4;
                font-family: "Segoe UI", sans-serif;
                font-size: 10pt;
            }}
            QCheckBox {{
                color: #CDD6F4;
                font-family: "Segoe UI", sans-serif;
                font-size: 9.5pt;
            }}
            QPushButton {{
                background-color: #89B4FA;
                color: #11111B;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-family: "Segoe UI", sans-serif;
                font-weight: bold;
                font-size: 9.5pt;
            }}
            QPushButton:hover {{
                background-color: #A6E3A1;
            }}
            QPushButton#btnCancel {{
                background-color: #45475A;
                color: #CDD6F4;
            }}
            QPushButton#btnCancel:hover {{
                background-color: #585B70;
            }}
            QLineEdit {{
                background-color: #313244;
                border: 1px solid #45475A;
                border-radius: 6px;
                color: #CDD6F4;
                padding: 6px;
                font-family: "Consolas", monospace;
                font-size: 10pt;
            }}
            QLineEdit:focus {{
                border: 1px solid #89B4FA;
            }}
        """)
        
        inner_layout = QVBoxLayout(self.container)
        inner_layout.setContentsMargins(18, 10, 18, 18)
        inner_layout.setSpacing(12)
        
        # Custom title/drag bar
        title_bar = QHBoxLayout()
        lbl_title = QLabel("Algorithmica Studio Voice Typist Settings")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 11pt; color: #89B4FA;")
        
        btn_close = QPushButton("×")
        btn_close.setToolTip("Close Settings")
        btn_close.setFixedSize(22, 22)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border-radius: 11px;
                color: #A6ADC8;
                font-size: 14pt;
                font-weight: normal;
                padding: 0;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 60);
                color: #EF4444;
            }
        """)
        btn_close.clicked.connect(self.reject)
        
        title_bar.addWidget(lbl_title)
        title_bar.addStretch()
        title_bar.addWidget(btn_close)
        inner_layout.addLayout(title_bar)
        
        # Separator line
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 15);")
        inner_layout.addWidget(sep)
        
        # API Key Field
        lbl_api = QLabel("AssemblyAI API Key:")
        self.ent_api = QLineEdit()
        self.ent_api.setEchoMode(QLineEdit.EchoMode.Password)
        self.ent_api.setText(self.current_config.get("api_key", ""))
        self.ent_api.setToolTip("<b>Double-click</b> to show/hide API key")
        self.ent_api.mouseDoubleClickEvent = lambda e: self.toggle_api_visibility()
        
        inner_layout.addWidget(lbl_api)
        inner_layout.addWidget(self.ent_api)
        
        # Hotkeys Row
        hotkey_layout = QHBoxLayout()
        
        v_start = QVBoxLayout()
        lbl_start = QLabel("Start Hotkey:")
        self.ent_start = HotkeyLineEdit()
        self.ent_start.setText(self.current_config.get("start_hotkey", "ctrl+shift+d"))
        v_start.addWidget(lbl_start)
        v_start.addWidget(self.ent_start)
        
        v_stop = QVBoxLayout()
        lbl_stop = QLabel("Stop Hotkey:")
        self.ent_stop = HotkeyLineEdit()
        self.ent_stop.setText(self.current_config.get("stop_hotkey", "enter"))
        v_stop.addWidget(lbl_stop)
        v_stop.addWidget(self.ent_stop)
        
        hotkey_layout.addLayout(v_start)
        hotkey_layout.addLayout(v_stop)
        inner_layout.addLayout(hotkey_layout)
        
        # Options Row
        options_layout = QHBoxLayout()
        self.chk_sound = QCheckBox("Enable Click Sounds")
        self.chk_sound.setToolTip("Play click sound effects when starting and stopping recordings")
        self.chk_sound.setChecked(self.current_config.get("sound_effects", True))
        
        self.chk_startup = QCheckBox("Run on Windows Startup")
        self.chk_startup.setToolTip("Automatically launch this app in the background when Windows boots up")
        self.chk_startup.setChecked(self.current_config.get("run_on_startup", False))
        
        options_layout.addWidget(self.chk_sound)
        options_layout.addWidget(self.chk_startup)
        inner_layout.addLayout(options_layout)
        
        # Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("btnCancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        inner_layout.addLayout(btn_layout)
        
        self.layout.addWidget(self.container)
        
        # Card shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

    def toggle_api_visibility(self):
        if self.ent_api.echoMode() == QLineEdit.EchoMode.Password:
            self.ent_api.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.ent_api.setEchoMode(QLineEdit.EchoMode.Password)

    # Window dragging handlers
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def save(self):
        api = self.ent_api.text().strip()
        start = self.ent_start.text().strip().lower()
        stop = self.ent_stop.text().strip().lower()
        sound = self.chk_sound.isChecked()
        startup = self.chk_startup.isChecked()

        if not api:
            QMessageBox.warning(self, "Validation Error", "API Key cannot be empty.")
            return
        if not start or not stop:
            QMessageBox.warning(self, "Validation Error", "Hotkeys cannot be empty.")
            return

        new_config = {
            "api_key": api,
            "start_hotkey": start,
            "stop_hotkey": stop,
            "window_x": self.current_config.get("window_x"),
            "window_y": self.current_config.get("window_y"),
            "sound_effects": sound,
            "run_on_startup": startup
        }
        
        if self.save_callback(new_config):
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Failed to save configuration.")

class HoveringRibbon(QWidget):
    """
    The main glassmorphic hovering capsule ribbon widget.
    Thinner & shorter pill design with dynamic cancel button, settings icon,
    and HTML custom-styled guide tooltips.
    """
    def __init__(self, current_config, save_config_callback, on_record_click, on_stop_click, on_exit_callback):
        super().__init__()
        self.config_data = current_config
        self.save_config_callback = save_config_callback
        self.on_record_click = on_record_click
        self.on_stop_click = on_stop_click
        self.on_exit_callback = on_exit_callback
        
        self.drag_position = QPoint()
        self.status = "Idle"
        self.is_dragging = False
        
        self.init_ui()

    def init_ui(self):
        # Apply global stylesheet for custom styled ToolTips
        self.setStyleSheet(GLOBAL_STYLE)
        
        # Borderless, Tool window, Stays on top, No Focus stealing
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Tool |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Thinner, shorter capsule size (width 190, height 36)
        self.setFixedSize(190, 36)
        
        # Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        
        # Capsule Frame
        self.container = QWidget(self)
        self.container.setObjectName("Capsule")
        self.container.setStyleSheet(f"""
            QWidget#Capsule {{
                background-color: {COLOR_BG};
                border: 1px solid {COLOR_BORDER};
                border-radius: 16px;
            }}
        """)
        self.container.setToolTip("<b>Voice Typist Status Pill</b><br>Click to start dictating or press Ctrl+Shift+D")
        
        inner_layout = QHBoxLayout(self.container)
        inner_layout.setContentsMargins(8, 0, 8, 0)
        inner_layout.setSpacing(4)
        
        # 1. Cancel button (Left end, always visible but faded when idle)
        self.btn_cancel = QPushButton("✕", self.container)
        self.btn_cancel.setToolTip("<b>Cancel Recording</b><br>Discard current speech (Esc)")
        self.btn_cancel.setFixedSize(22, 22)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 11px;
                color: rgba(239, 68, 68, 80);
                font-size: 9pt;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 50);
                color: #EF4444;
            }
            QPushButton:pressed {
                background-color: rgba(239, 68, 68, 20);
            }
        """)
        self.btn_cancel.setEnabled(False)  # Disabled when not recording
        self.btn_cancel.clicked.connect(self.on_record_click)
        inner_layout.addWidget(self.btn_cancel)
        
        # 2. Waveform visualizer (stretch center)
        self.wave = WaveformWidget(self.container)
        inner_layout.addWidget(self.wave)
        
        # 3. Settings button (Right end)
        self.btn_settings = QPushButton("⚙️", self.container)
        self.btn_settings.setToolTip("<b>Configure Settings</b><br>Setup AssemblyAI key, startup, and sound options")
        self.btn_settings.setFixedSize(22, 22)
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 11px;
                color: #CDD6F4;
                font-size: 9pt;
                padding: 0;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 30);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 15);
            }
        """)
        self.btn_settings.clicked.connect(self.open_settings_dialog)
        inner_layout.addWidget(self.btn_settings)
        
        self.main_layout.addWidget(self.container)
        
        # Capsule drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 3)
        self.container.setGraphicsEffect(shadow)
        
        self.restore_position()
        self.setWindowOpacity(0.50)

    def restore_position(self):
        x = self.config_data.get("window_x")
        y = self.config_data.get("window_y")
        screen = QApplication.primaryScreen().geometry()
        
        if x is not None and y is not None:
            x = max(0, min(x, screen.width() - self.width()))
            y = max(0, min(y, screen.height() - self.height()))
            self.move(x, y)
        else:
            self.move((screen.width() - self.width()) // 2, screen.height() - 110)

    def update_volume(self, volume):
        self.wave.set_volume(volume)

    def update_status(self, status, msg=""):
        self.status = status
        self.wave.set_status(status)
        
        if status == "Recording":
            # Fully bright and enabled during recording
            self.btn_cancel.setEnabled(True)
            self.btn_cancel.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 11px;
                    color: #EF4444;
                    font-size: 9pt;
                    font-weight: bold;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 60);
                }
                QPushButton:pressed {
                    background-color: rgba(239, 68, 68, 25);
                }
            """)
            self.container.setToolTip("<b>Recording...</b><br>Click capsule bar to stop & paste (Enter), or Esc to cancel")
            self.setWindowOpacity(1.0)
        else:
            # Faded and disabled when not recording
            self.btn_cancel.setEnabled(False)
            self.btn_cancel.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    border-radius: 11px;
                    color: rgba(239, 68, 68, 70);
                    font-size: 9pt;
                    font-weight: bold;
                    padding: 0;
                }
                QPushButton:hover {
                    background-color: rgba(239, 68, 68, 30);
                    color: rgba(239, 68, 68, 130);
                }
            """)
            if status == "Transcribing":
                self.container.setToolTip("<b>Processing Speech...</b><br>Algorithmica Studio is transcribing your audio")
            elif status == "Error":
                self.container.setToolTip(f"<b>Error State</b><br>{msg}. Click capsule to reset.")
            else: # Idle
                self.container.setToolTip("<b>Voice Typist Status Pill</b><br>Click to start dictating or press your start hotkey")
                self.setWindowOpacity(0.50)

    # Hover events opacity transitions
    def enterEvent(self, event):
        self.setWindowOpacity(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.status != "Recording":
            self.setWindowOpacity(0.50)
        super().leaveEvent(event)

    # Mouse events dragging & click-to-record
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.drag_start_pos = event.globalPosition().toPoint()
            self.is_dragging = False
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = (event.globalPosition().toPoint() - self.drag_start_pos).manhattanLength()
            if delta > 3:
                self.is_dragging = True
                self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_dragging:
                pos = self.pos()
                self.config_data["window_x"] = pos.x()
                self.config_data["window_y"] = pos.y()
                self.save_config_callback(self.config_data)
            else:
                child = self.childAt(event.position().toPoint())
                if child != self.btn_settings and child != self.btn_cancel:
                    self.toggle_recording_click()
            event.accept()

    def toggle_recording_click(self):
        if self.status == "Idle":
            self.on_record_click()
        elif self.status == "Recording":
            self.on_stop_click()
        elif self.status == "Error":
            self.update_status("Idle")

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E1E2E;
                color: #CDD6F4;
                border: 1px solid #45475A;
                font-family: "Segoe UI";
            }
            QMenu::item:selected {
                background-color: #89B4FA;
                color: #11111B;
            }
        """)
        
        act_settings = QAction("⚙️ Settings", self)
        act_settings.triggered.connect(self.open_settings_dialog)
        
        act_reset = QAction("🔄 Reset Position", self)
        act_reset.triggered.connect(self.reset_position)
        
        menu.addSeparator()
        
        act_exit = QAction("❌ Exit App", self)
        act_exit.triggered.connect(self.on_exit_callback)
        
        menu.addAction(act_settings)
        menu.addAction(act_reset)
        menu.addSeparator()
        menu.addAction(act_exit)
        
        menu.exec(event.globalPos())

    def reset_position(self):
        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - self.width()) // 2, screen.height() - 110)
        pos = self.pos()
        self.config_data["window_x"] = pos.x()
        self.config_data["window_y"] = pos.y()
        self.save_config_callback(self.config_data)

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.config_data, self.save_settings_callback, self)
        dialog.exec()

    def save_settings_callback(self, new_config):
        self.config_data = new_config
        return self.save_config_callback(new_config)
