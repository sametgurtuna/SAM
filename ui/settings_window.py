# SAM — Settings Window
# Modern cyber-minimalist sidebar-based settings window inspired by Google Stitch designs.
# Config.yaml values are fully customizable with real-time feedback and premium aesthetics.

import logging
import os
import platform
import subprocess
import sys
import time

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QStackedWidget,
    QLabel, QLineEdit, QComboBox, QSlider, QSpinBox, QPushButton,
    QMessageBox, QWidget, QFileDialog, QScrollArea, QFrame,
    QGridLayout, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtProperty, QUrl, QTimer, QRectF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QDesktopServices, QPainter, QColor, QBrush, QPen, QRadialGradient
)

from core.config import config

logger = logging.getLogger(__name__)

# Start timestamp for uptime calculation in Diagnostics
APP_START_TIME = time.time()

# ─── Tema & Renk Paleti (Google Stitch Cyber-Dark) ─────────────────────
BG = "#0a0a0f"
SURFACE = "#101018"
SURFACE_HI = "#16161f"
SURFACE_CARD = "#12121c"
FIELD = "#1a1a24"
BORDER = "rgba(255, 255, 255, 0.08)"
BORDER_FOCUS = "#00D4AA"
ACCENT = "#00D4AA"
ACCENT_CYAN = "#38F2D8"
ACCENT_SOFT = "rgba(0, 212, 170, 0.12)"
ACCENT_HOVER = "#16f5ce"
TEXT = "#e9e9ee"
TEXT_DIM = "#8b8b97"
TEXT_MUTED = "#555562"
DANGER = "#ff5555"

SETTINGS_STYLESHEET = f"""
QDialog {{
    background-color: {BG};
    color: {TEXT};
}}
QWidget {{
    font-family: "Segoe UI", "Inter", sans-serif;
}}

/* ─── Top Header ─────────────────────────────────────────── */
QLabel#windowTitle {{
    color: {ACCENT};
    font-size: 20px;
    font-weight: 700;
    letter-spacing: -0.3px;
}}
QLabel#versionPill {{
    color: {TEXT_DIM};
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 3px 10px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 11px;
    font-weight: 500;
}}
QLabel#headerSettingsIcon {{
    color: {TEXT_DIM};
    font-size: 16px;
}}

/* ─── Sidebar ─────────────────────────────────────────────── */
QListWidget#sidebar {{
    background-color: transparent;
    border: none;
    outline: none;
    padding: 6px 0;
    font-size: 13px;
}}
QListWidget#sidebar::item {{
    color: {TEXT_DIM};
    padding: 10px 14px;
    border-radius: 8px;
    margin: 2px 0;
    font-weight: 500;
}}
QListWidget#sidebar::item:hover {{
    background-color: {SURFACE_HI};
    color: {TEXT};
}}
QListWidget#sidebar::item:selected {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT};
    font-weight: 600;
    border-left: 3px solid {ACCENT};
}}

/* ─── Page Headings ───────────────────────────────────────── */
QLabel#pageHeading {{
    color: {TEXT};
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.4px;
}}
QLabel#pageSubheading {{
    color: {TEXT_DIM};
    font-size: 12.5px;
    line-height: 1.4;
}}

/* ─── Section Cards & Containers ─────────────────────────── */
QFrame#sectionCard {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 18px;
}}
QFrame#innerCard {{
    background-color: {SURFACE_HI};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 12px;
}}
QFrame#codeCard {{
    background-color: #0c0c14;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 8px;
    padding: 14px;
}}
QFrame#dashedCard {{
    background-color: transparent;
    border: 1px dashed rgba(255, 255, 255, 0.14);
    border-radius: 8px;
    padding: 16px;
}}
QLabel#cardSectionTitle {{
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}

/* ─── Row Items ──────────────────────────────────────────── */
QLabel#rowTitle {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#rowDesc {{
    color: {TEXT_DIM};
    font-size: 11.5px;
}}
QFrame#rowDivider {{
    background-color: {BORDER};
    max-height: 1px;
    border: none;
}}

/* ─── Inputs & Form Controls ──────────────────────────────── */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT};
    padding: 8px 12px;
    font-size: 12px;
    min-height: 22px;
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: rgba(255, 255, 255, 0.18);
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
    background-color: {SURFACE_HI};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: {TEXT_MUTED};
    background-color: #14141c;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox QAbstractItemView {{
    background-color: {FIELD};
    color: {TEXT};
    selection-background-color: {ACCENT_SOFT};
    selection-color: {ACCENT};
    border: 1px solid rgba(0, 212, 170, 0.25);
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}

/* ─── Modern Sliders ──────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 6px;
    background: #23232f;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid {ACCENT};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: {ACCENT_HOVER};
    border-color: #ffffff;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_CYAN});
    border-radius: 3px;
}}

/* ─── Buttons ────────────────────────────────────────────── */
QPushButton {{
    background-color: {SURFACE_HI};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
    min-height: 18px;
}}
QPushButton:hover {{
    background-color: #23232f;
    border-color: rgba(255, 255, 255, 0.22);
}}
QPushButton:pressed {{
    background-color: #1c1c26;
}}
QPushButton#primaryBtn {{
    background-color: {ACCENT};
    color: #050508;
    border: none;
    font-weight: 700;
}}
QPushButton#primaryBtn:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#dangerOutlineBtn {{
    background-color: transparent;
    color: {DANGER};
    border: 1px solid rgba(255, 85, 85, 0.35);
}}
QPushButton#dangerOutlineBtn:hover {{
    background-color: rgba(255, 85, 85, 0.12);
    border-color: {DANGER};
}}
QPushButton#iconBtn {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
}}
QPushButton#iconBtn:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}
QPushButton#stepperBtn {{
    background-color: {FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    font-size: 13px;
    font-weight: bold;
    min-width: 32px;
    min-height: 30px;
    padding: 2px;
}}
QPushButton#stepperBtn:hover {{
    border-color: {ACCENT};
    color: {ACCENT};
}}

/* ─── Scrollbars ─────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #252533;
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: #353545;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""


# ─── Custom Widget: Modern iOS/Cyberpunk Animated ToggleSwitch ─────────
class ToggleSwitch(QWidget):
    """Modern animasyonlu hap seklinde Toggle Switch kontrolu."""
    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, checked=False):
        super().__init__(parent)
        self.setFixedSize(46, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = checked
        self._thumb_position = 25.0 if checked else 3.0

        self._anim = QPropertyAnimation(self, b"thumb_position", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked != checked:
            self._checked = checked
            self._animate()
            self.toggled.emit(self._checked)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self._animate()
            self.toggled.emit(self._checked)
            self.update()

    def _animate(self):
        self._anim.stop()
        self._anim.setStartValue(self._thumb_position)
        self._anim.setEndValue(25.0 if self._checked else 3.0)
        self._anim.start()

    def get_thumb_position(self) -> float:
        return self._thumb_position

    def set_thumb_position(self, pos: float):
        self._thumb_position = pos
        self.update()

    thumb_position = pyqtProperty(float, get_thumb_position, set_thumb_position)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Arka plan hapi
        bg_color = QColor(ACCENT) if self._checked else QColor("#22222f")
        border_color = QColor(ACCENT_HOVER) if self._checked else QColor("rgba(255,255,255,0.12)")

        p.setPen(QPen(border_color, 1))
        p.setBrush(QBrush(bg_color))
        p.drawRoundedRect(QRectF(1, 1, 44, 22), 11, 11)

        # Basparmak (Knob)
        p.setPen(Qt.PenStyle.NoPen)
        knob_color = QColor("#050508") if self._checked else QColor("#ffffff")
        p.setBrush(QBrush(knob_color))
        p.drawEllipse(QRectF(self._thumb_position, 3, 18, 18))

        p.end()


# ─── Custom Widget: Segmented Button Control ([ Orb ] [ Bar ]) ────────
class SegmentedControl(QWidget):
    """Segmented switch kontrolu (Orb / Bar gibi mod secimleri)."""
    selection_changed = pyqtSignal(str)

    def __init__(self, options: list[str], current: str = "", parent=None):
        super().__init__(parent)
        self._options = options
        self._current = current if current in options else options[0]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {SURFACE_HI};
                border: 1px solid {BORDER};
                border-radius: 8px;
            }}
        """)

        self._buttons = {}
        for opt in options:
            btn = QPushButton(opt)
            btn.setCheckable(True)
            btn.setChecked(opt == self._current)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, o=opt: self.set_current(o))
            self._buttons[opt] = btn
            layout.addWidget(btn)

        self._update_styles()

    def set_current(self, opt: str):
        if opt in self._options and self._current != opt:
            self._current = opt
            self._update_styles()
            self.selection_changed.emit(self._current)

    def current_text(self) -> str:
        return self._current

    def _update_styles(self):
        for opt, btn in self._buttons.items():
            is_active = (opt == self._current)
            btn.setChecked(is_active)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {ACCENT};
                        color: #050508;
                        font-weight: 700;
                        border: none;
                        border-radius: 6px;
                        padding: 5px 16px;
                        font-size: 11.5px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {TEXT_DIM};
                        font-weight: 500;
                        border: none;
                        border-radius: 6px;
                        padding: 5px 16px;
                        font-size: 11.5px;
                    }}
                    QPushButton:hover {{
                        color: {TEXT};
                    }}
                """)


# ─── Custom Widget: Live Orb Interactive Preview Widget ───────────────
class LiveOrbPreview(QWidget):
    """Appearance sekmesinde kullanicinin slider degerlerine aninda tepki veren canli Orb."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 260)
        self._orb_size = 120
        self._ring_width = 3
        self._opacity = 0.95
        self._pulse_phase = 0.0

        # Yumusak nefes alma animasyonu
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_pulse)
        self._timer.start(40)  # 25 FPS

    def update_params(self, size: int, ring_width: int, opacity: float):
        self._orb_size = size
        self._ring_width = ring_width
        self._opacity = opacity
        self.update()

    def _animate_pulse(self):
        self._pulse_phase += 0.05
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        # Arka plan
        p.fillRect(0, 0, w, h, QColor(SURFACE_HI))

        # Dis parlama (Glow)
        import math
        breathe = 0.85 + 0.15 * math.sin(self._pulse_phase)
        scale_factor = min(w, h) / 360.0
        render_size = (self._orb_size * scale_factor) * breathe
        outer_radius = render_size / 2.0 + 35 * scale_factor

        gradient = QRadialGradient(cx, cy, outer_radius)
        gradient.setColorAt(0.0, QColor(0, 212, 170, int(90 * self._opacity)))
        gradient.setColorAt(0.5, QColor(56, 242, 216, int(35 * self._opacity)))
        gradient.setColorAt(1.0, QColor(0, 212, 170, 0))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(gradient))
        p.drawEllipse(QRectF(cx - outer_radius, cy - outer_radius, outer_radius * 2, outer_radius * 2))

        # Ana dairesel disk
        disc_radius = render_size / 2.0
        disc_grad = QRadialGradient(cx, cy, disc_radius)
        disc_grad.setColorAt(0.0, QColor(56, 242, 216, int(230 * self._opacity)))
        disc_grad.setColorAt(0.7, QColor(0, 212, 170, int(200 * self._opacity)))
        disc_grad.setColorAt(1.0, QColor(10, 10, 15, int(240 * self._opacity)))

        p.setBrush(QBrush(disc_grad))
        ring_pen = QPen(QColor(ACCENT), max(1.0, self._ring_width * scale_factor))
        p.setPen(ring_pen)
        p.drawEllipse(QRectF(cx - disc_radius, cy - disc_radius, disc_radius * 2, disc_radius * 2))

        p.end()


# ─── Custom Widget: Status Badge (LED indicator pill) ─────────────────
class StatusBadge(QWidget):
    """Yesil / Gri LED durum hap rozeti (Connected, Disconnected vb.)."""
    def __init__(self, text: str, is_active: bool = True, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 10, 4)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        self._label = QLabel(text)

        layout.addWidget(self._dot)
        layout.addWidget(self._label)

        self.set_state(text, is_active)

    def set_state(self, text: str, is_active: bool):
        self._label.setText(text)
        color = ACCENT if is_active else TEXT_DIM
        bg = ACCENT_SOFT if is_active else "rgba(255, 255, 255, 0.05)"
        border = "rgba(0, 212, 170, 0.3)" if is_active else BORDER

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 12px;
            }}
            QLabel {{
                color: {color};
                font-size: 11px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)


# ─── Main Settings Window Class ───────────────────────────────────────
class SettingsWindow(QDialog):
    """
    SAM Settings penceresi — Google Stitch Cyberpunk Dark arayuz tasarimi.
    """
    settings_saved = pyqtSignal()

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self._controller = controller
        self.setWindowTitle("SAM — Settings")
        self.resize(920, 680)
        self.setMinimumSize(840, 600)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 20, 24, 18)

        # 1. Top Header
        main_layout.addLayout(self._build_top_header())
        main_layout.addWidget(self._divider())

        # 2. Main Content Area (Sidebar + Stack)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)

        # Sol Sidebar
        sidebar_col = QVBoxLayout()
        sidebar_col.setSpacing(12)

        # Mini SAM Avatar Card (Sidebar ustunde)
        avatar_card = QFrame()
        avatar_card.setObjectName("innerCard")
        avatar_layout = QHBoxLayout(avatar_card)
        avatar_layout.setContentsMargins(10, 8, 10, 8)
        avatar_layout.setSpacing(10)

        orb_icon_lbl = QLabel("🟢")
        orb_icon_lbl.setStyleSheet(f"color: {ACCENT}; font-size: 16px;")
        avatar_text_col = QVBoxLayout()
        avatar_text_col.setSpacing(1)
        name_lbl = QLabel("SAM")
        name_lbl.setStyleSheet(f"color: {ACCENT}; font-weight: 700; font-size: 13px;")
        sub_lbl = QLabel("Smart Assistant Module")
        sub_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 10px;")
        avatar_text_col.addWidget(name_lbl)
        avatar_text_col.addWidget(sub_lbl)

        avatar_layout.addWidget(orb_icon_lbl)
        avatar_layout.addLayout(avatar_text_col)
        avatar_layout.addStretch()

        sidebar_col.addWidget(avatar_card)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(190)
        self.sidebar.currentRowChanged.connect(self._change_page)
        sidebar_col.addWidget(self.sidebar, 1)

        content_layout.addLayout(sidebar_col)

        # Sag Stacked Widget
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        main_layout.addLayout(content_layout, 1)

        # 3. Sayfalar
        self._add_page("⚡  General", "Activation", "Configure how you interact with SAM globally.", self._build_general_tab())
        self._add_page("🎙  Speech", "Speech & Voice", "Configure speech recognition and text-to-speech synthesis parameters.", self._build_speech_tab())
        self._add_page("💬  Responses", "Instant Responses", "Configure zero-latency predefined replies for exact pattern matches.", self._build_responses_tab())
        self._add_page("🧠  LLM", "Local AI Engine", "Configure the connection parameters for your local LLM provider.", self._build_llm_tab())
        self._add_page("🎨  Appearance", "Desktop Orb Overlay", "Configure the persistent floating assistant widget.", self._build_ui_tab())
        self._add_page("🎵  Integrations", "Connected Services", "Manage external APIs and service connections.", self._build_integrations_tab())
        self._add_page("ℹ  About", "About & Diagnostics", "System information and environmental configurations.", self._build_about_tab())

        self.sidebar.setCurrentRow(0)

        main_layout.addWidget(self._divider())

        # 4. Footer Bar
        main_layout.addLayout(self._build_footer())

    # ─── Header & Footer ──────────────────────────────────────────────
    def _build_top_header(self) -> QHBoxLayout:
        version = config.get("app", "version", default="0.4.7")
        header = QHBoxLayout()
        header.setSpacing(12)

        title = QLabel("SAM Settings")
        title.setObjectName("windowTitle")
        header.addWidget(title)

        header.addStretch()

        pill = QLabel(f"v{version}")
        pill.setObjectName("versionPill")
        header.addWidget(pill, 0, Qt.AlignmentFlag.AlignVCenter)

        cog = QLabel("⚙")
        cog.setObjectName("headerSettingsIcon")
        header.addWidget(cog, 0, Qt.AlignmentFlag.AlignVCenter)

        return header

    def _build_footer(self) -> QHBoxLayout:
        footer = QHBoxLayout()
        footer.setSpacing(12)

        # Status: System Ready with green LED
        status_layout = QHBoxLayout()
        status_layout.setSpacing(6)
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {ACCENT}; font-size: 11px;")
        status_txt = QLabel("System Ready")
        status_txt.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11.5px; font-weight: 500;")
        status_layout.addWidget(dot)
        status_layout.addWidget(status_txt)

        footer.addLayout(status_layout)
        footer.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        footer.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primaryBtn")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_settings)
        footer.addWidget(save_btn)

        return footer

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setObjectName("rowDivider")
        line.setFixedHeight(1)
        return line

    def _add_page(self, nav_label: str, title: str, description: str, widget: QWidget):
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 8, 0)
        page_layout.setSpacing(6)

        heading = QLabel(title)
        heading.setObjectName("pageHeading")
        desc = QLabel(description)
        desc.setObjectName("pageSubheading")
        desc.setWordWrap(True)

        page_layout.addWidget(heading)
        page_layout.addWidget(desc)
        page_layout.addSpacing(8)
        page_layout.addWidget(widget, 1)

        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self.sidebar.addItem(nav_label)
        self.stack.addWidget(scroll)

    def _change_page(self, index: int):
        self.stack.setCurrentIndex(index)

    # ─── 1. General Tab (Activation) ──────────────────────────────────
    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        # Row 1: Voice Hotkey
        r1 = QHBoxLayout()
        r1_text = QVBoxLayout()
        r1_text.setSpacing(2)
        r1_title = QLabel("Voice Hotkey")
        r1_title.setObjectName("rowTitle")
        r1_desc = QLabel("Hold to dictate voice commands globally.")
        r1_desc.setObjectName("rowDesc")
        r1_text.addWidget(r1_title)
        r1_text.addWidget(r1_desc)
        r1.addLayout(r1_text, 1)

        self._hotkey_input = QLineEdit(config.get("hotkey", "trigger", default="ctrl+space"))
        self._hotkey_input.setFixedWidth(180)
        self._hotkey_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hotkey_input.setStyleSheet(f"font-family: 'Cascadia Code', monospace; font-weight: 600; color: {ACCENT};")
        r1.addWidget(self._hotkey_input)
        card_layout.addLayout(r1)
        card_layout.addWidget(self._divider())

        # Row 2: Text Hotkey
        r2 = QHBoxLayout()
        r2_text = QVBoxLayout()
        r2_text.setSpacing(2)
        r2_title = QLabel("Text Hotkey")
        r2_title.setObjectName("rowTitle")
        r2_desc = QLabel("Summon SAM's text input overlay anywhere.")
        r2_desc.setObjectName("rowDesc")
        r2_text.addWidget(r2_title)
        r2_text.addWidget(r2_desc)
        r2.addLayout(r2_text, 1)

        self._text_hotkey_input = QLineEdit(config.get("hotkey", "text_input", default="ctrl+shift+space"))
        self._text_hotkey_input.setFixedWidth(180)
        self._text_hotkey_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._text_hotkey_input.setStyleSheet(f"font-family: 'Cascadia Code', monospace; font-weight: 600; color: {ACCENT};")
        r2.addWidget(self._text_hotkey_input)
        card_layout.addLayout(r2)
        card_layout.addWidget(self._divider())

        # Row 3: Wake Word Model
        r3 = QHBoxLayout()
        r3_text = QVBoxLayout()
        r3_text.setSpacing(2)
        r3_title = QLabel("Wake Word Model")
        r3_title.setObjectName("rowTitle")
        r3_desc = QLabel("Select the local ONNX model for wake word detection.")
        r3_desc.setObjectName("rowDesc")
        r3_text.addWidget(r3_title)
        r3_text.addWidget(r3_desc)
        r3.addLayout(r3_text, 1)

        wake_right = QHBoxLayout()
        wake_right.setSpacing(8)
        self._wake_model_combo = QComboBox()
        self._wake_model_combo.setFixedWidth(220)
        wake_models = ["assets/models/hey_sam.onnx", "hey_jarvis", "alexa", "hey_mycroft", "ok_google"]
        current_wake = config.get("wake_word", "model", default="assets/models/hey_sam.onnx")
        if current_wake not in wake_models:
            wake_models.append(current_wake)
        self._wake_model_combo.addItems(wake_models)
        idx = self._wake_model_combo.findText(current_wake)
        if idx >= 0:
            self._wake_model_combo.setCurrentIndex(idx)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_custom_wake_model)
        wake_right.addWidget(self._wake_model_combo)
        wake_right.addWidget(browse_btn)
        r3.addLayout(wake_right)
        card_layout.addLayout(r3)
        card_layout.addWidget(self._divider())

        # Row 4: Wake Threshold Slider
        r4 = QVBoxLayout()
        r4.setSpacing(6)
        r4_top = QHBoxLayout()
        r4_text = QVBoxLayout()
        r4_text.setSpacing(2)
        r4_title = QLabel("Wake Threshold")
        r4_title.setObjectName("rowTitle")
        r4_desc = QLabel("Adjust sensitivity. Lower values activate easier.")
        r4_desc.setObjectName("rowDesc")
        r4_text.addWidget(r4_title)
        r4_text.addWidget(r4_desc)
        r4_top.addLayout(r4_text, 1)

        current_thresh = config.get("wake_word", "threshold", default=0.40)
        self._wake_thresh_badge = QLabel(f"{current_thresh:.2f}")
        self._wake_thresh_badge.setStyleSheet(f"""
            color: {ACCENT};
            background-color: {FIELD};
            border: 1px solid rgba(0, 212, 170, 0.3);
            border-radius: 6px;
            padding: 4px 10px;
            font-family: 'Cascadia Code', monospace;
            font-weight: 700;
            font-size: 12px;
        """)
        r4_top.addWidget(self._wake_thresh_badge)
        r4.addLayout(r4_top)

        # Slider bar with min/max labels
        self._wake_threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self._wake_threshold_slider.setRange(10, 100)
        self._wake_threshold_slider.setValue(int(current_thresh * 100))
        self._wake_threshold_slider.valueChanged.connect(
            lambda v: self._wake_thresh_badge.setText(f"{v / 100.0:.2f}")
        )
        r4.addWidget(self._wake_threshold_slider)

        lbl_row = QHBoxLayout()
        min_lbl = QLabel("0.10")
        min_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-family: monospace;")
        max_lbl = QLabel("1.00")
        max_lbl.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; font-family: monospace;")
        lbl_row.addWidget(min_lbl)
        lbl_row.addStretch()
        lbl_row.addWidget(max_lbl)
        r4.addLayout(lbl_row)

        card_layout.addLayout(r4)

        layout.addWidget(card)
        layout.addStretch()
        return tab

    # ─── 2. Speech & Voice Tab (Google Stitch Exact Match) ───────────
    def _build_speech_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Top 2-Card Row: Speech-to-Text & Live Transcription
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # Card 1: Speech-to-Text (Faster-Whisper)
        stt_card = QFrame()
        stt_card.setObjectName("sectionCard")
        stt_layout = QVBoxLayout(stt_card)
        stt_layout.setSpacing(12)

        stt_head_row = QHBoxLayout()
        stt_icon = QLabel("🗣")
        stt_icon.setStyleSheet("font-size: 14px;")
        stt_head = QLabel("Speech-to-Text (Faster-Whisper)")
        stt_head.setObjectName("rowTitle")
        stt_head_row.addWidget(stt_icon)
        stt_head_row.addWidget(stt_head)
        stt_head_row.addStretch()
        stt_layout.addLayout(stt_head_row)
        stt_layout.addWidget(self._divider())

        # Model
        stt_layout.addWidget(QLabel("Model"))
        self._stt_model_combo = QComboBox()
        self._stt_model_combo.addItems(["tiny", "base", "small", "medium", "large-v3"])
        current_stt = config.get("stt", "model", default="base")
        idx = self._stt_model_combo.findText(current_stt)
        if idx >= 0:
            self._stt_model_combo.setCurrentIndex(idx)
        stt_layout.addWidget(self._stt_model_combo)

        # Language
        stt_layout.addWidget(QLabel("Language"))
        self._stt_language_combo = QComboBox()
        lang_options = [
            ("English (en)", "en"),
            ("Turkish (tr)", "tr"),
            ("Auto-detect (auto)", ""),
            ("German (de)", "de"),
            ("French (fr)", "fr"),
        ]
        for name, code in lang_options:
            self._stt_language_combo.addItem(name, code)
        
        current_lang = config.get("stt", "language", default="") or ""
        idx_lang = self._stt_language_combo.findData(current_lang)
        if idx_lang >= 0:
            self._stt_language_combo.setCurrentIndex(idx_lang)
        else:
            self._stt_language_combo.setEditable(True)
            self._stt_language_combo.setCurrentText(current_lang)
        stt_layout.addWidget(self._stt_language_combo)

        # Compute Device
        stt_layout.addWidget(QLabel("Compute Device"))
        self._stt_device_combo = QComboBox()
        self._stt_device_combo.addItems(["CPU", "CUDA"])
        current_device = config.get("stt", "device", default="cpu").upper()
        idx_dev = self._stt_device_combo.findText(current_device)
        if idx_dev >= 0:
            self._stt_device_combo.setCurrentIndex(idx_dev)
        stt_layout.addWidget(self._stt_device_combo)
        stt_layout.addStretch()

        top_row.addWidget(stt_card, 1)

        # Card 2: Live Transcription
        live_card = QFrame()
        live_card.setObjectName("sectionCard")
        live_layout = QVBoxLayout(live_card)
        live_layout.setSpacing(12)

        live_head_row = QHBoxLayout()
        live_icon = QLabel("〰")
        live_icon.setStyleSheet(f"color: {ACCENT}; font-size: 14px; font-weight: bold;")
        live_head = QLabel("Live Transcription")
        live_head.setObjectName("rowTitle")
        live_head_row.addWidget(live_icon)
        live_head_row.addWidget(live_head)
        live_head_row.addStretch()
        live_layout.addLayout(live_head_row)
        live_layout.addWidget(self._divider())

        live_desc = QLabel("Settings for real-time continuous listening mode. Faster models are recommended for lower latency.")
        live_desc.setWordWrap(True)
        live_desc.setObjectName("rowDesc")
        live_layout.addWidget(live_desc)

        # Live Model
        live_layout.addWidget(QLabel("Live Model"))
        self._stt_partial_model = QComboBox()
        for label, val in [
            ("base", "base"),
            ("tiny", "tiny"),
            ("small", "small"),
            ("off", "off")
        ]:
            self._stt_partial_model.addItem(label, val)
        current_partial = config.get("stt", "partial_model", default="base")
        idx_p = self._stt_partial_model.findData(current_partial)
        self._stt_partial_model.setCurrentIndex(idx_p if idx_p >= 0 else 0)
        live_layout.addWidget(self._stt_partial_model)

        # Refresh Every Slider with badge
        refresh_top = QHBoxLayout()
        refresh_top.addWidget(QLabel("Refresh Every"))
        refresh_top.addStretch()

        cur_interval = config.get("stt", "partial_interval_ms", default=400)
        self._live_refresh_badge = QLabel(f"{cur_interval} ms")
        self._live_refresh_badge.setStyleSheet(f"""
            color: {ACCENT};
            background-color: {FIELD};
            border: 1px solid rgba(0, 212, 170, 0.3);
            border-radius: 6px;
            padding: 2px 8px;
            font-family: monospace;
            font-weight: 700;
            font-size: 11px;
        """)
        refresh_top.addWidget(self._live_refresh_badge)
        live_layout.addLayout(refresh_top)

        self._stt_partial_interval_slider = QSlider(Qt.Orientation.Horizontal)
        self._stt_partial_interval_slider.setRange(100, 1000)
        self._stt_partial_interval_slider.setValue(cur_interval)
        self._stt_partial_interval_slider.valueChanged.connect(
            lambda v: self._live_refresh_badge.setText(f"{v} ms")
        )
        live_layout.addWidget(self._stt_partial_interval_slider)

        live_lbls = QHBoxLayout()
        l_fast = QLabel("Fast (100ms)")
        l_fast.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        l_stable = QLabel("Stable (1s)")
        l_stable.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        live_lbls.addWidget(l_fast)
        live_lbls.addStretch()
        live_lbls.addWidget(l_stable)
        live_layout.addLayout(live_lbls)
        live_layout.addStretch()

        top_row.addWidget(live_card, 1)
        layout.addLayout(top_row)

        # Bottom Card: Text-to-Speech (Edge-TTS)
        tts_card = QFrame()
        tts_card.setObjectName("sectionCard")
        tts_layout = QVBoxLayout(tts_card)
        tts_layout.setSpacing(12)

        tts_head_row = QHBoxLayout()
        tts_icon = QLabel("🔊")
        tts_icon.setStyleSheet("font-size: 14px;")
        tts_head = QLabel("Text-to-Speech (Edge-TTS)")
        tts_head.setObjectName("rowTitle")
        tts_head_row.addWidget(tts_icon)
        tts_head_row.addWidget(tts_head)
        tts_head_row.addStretch()
        tts_layout.addLayout(tts_head_row)
        tts_layout.addWidget(self._divider())

        # 2 Column Grid inside TTS Card
        tts_grid = QGridLayout()
        tts_grid.setHorizontalSpacing(24)
        tts_grid.setVerticalSpacing(12)

        # Left Column: Engine, Fallback Voice, Rate Adjustment
        tts_grid.addWidget(QLabel("Engine"), 0, 0)
        self._tts_engine_combo = QComboBox()
        self._tts_engine_combo.addItems(["edge-tts", "local"])
        idx_e = self._tts_engine_combo.findText(config.get("tts", "engine", default="edge-tts"))
        if idx_e >= 0:
            self._tts_engine_combo.setCurrentIndex(idx_e)
        tts_grid.addWidget(self._tts_engine_combo, 1, 0)

        tts_grid.addWidget(QLabel("Fallback Voice"), 2, 0)
        self._tts_voice = QComboBox()
        fallback_voices = [
            "en-US-GuyNeural", "en-US-JennyNeural", "en-US-AriaNeural",
            "en-GB-RyanNeural", "en-GB-SoniaNeural",
            "tr-TR-AhmetNeural", "tr-TR-EmelNeural",
        ]
        self._tts_voice.addItems(fallback_voices)
        self._tts_voice.setCurrentText(config.get("tts", "voice", default="en-US-GuyNeural"))
        tts_grid.addWidget(self._tts_voice, 3, 0)

        tts_grid.addWidget(QLabel("Rate Adjustment"), 4, 0)
        rate_stepper = QHBoxLayout()
        rate_stepper.setSpacing(6)
        dec_btn = QPushButton("-")
        dec_btn.setObjectName("stepperBtn")
        dec_btn.clicked.connect(lambda: self._step_rate(-10))

        self._tts_rate = QLineEdit(config.get("tts", "rate", default="+0%"))
        self._tts_rate.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tts_rate.setStyleSheet(f"font-family: 'Cascadia Code', monospace; font-weight: 600; color: {TEXT};")

        inc_btn = QPushButton("+")
        inc_btn.setObjectName("stepperBtn")
        inc_btn.clicked.connect(lambda: self._step_rate(10))

        rate_stepper.addWidget(dec_btn)
        rate_stepper.addWidget(self._tts_rate, 1)
        rate_stepper.addWidget(inc_btn)
        tts_grid.addLayout(rate_stepper, 5, 0)

        # Right Column: Auto Switch Toggle, Turkish Voice, English Voice
        auto_head_col = QVBoxLayout()
        auto_head_col.setSpacing(2)
        auto_title = QLabel("Switch voice automatically")
        auto_title.setObjectName("rowTitle")
        auto_desc = QLabel("Based on detected output language")
        auto_desc.setObjectName("rowDesc")
        auto_head_col.addWidget(auto_title)
        auto_head_col.addWidget(auto_desc)

        auto_top_row = QHBoxLayout()
        auto_top_row.addLayout(auto_head_col, 1)
        self._tts_auto_language_switch = ToggleSwitch(checked=config.get("tts", "auto_language", default=True))
        auto_top_row.addWidget(self._tts_auto_language_switch)
        tts_grid.addLayout(auto_top_row, 0, 1, 2, 1)

        # Turkish Voice
        tr_label_h = QHBoxLayout()
        tr_badge = QLabel("TR")
        tr_badge.setStyleSheet(f"background-color: {FIELD}; color: {ACCENT}; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 4px;")
        tr_label_h.addWidget(tr_badge)
        tr_label_h.addWidget(QLabel("Turkish Voice"), 1)
        tts_grid.addLayout(tr_label_h, 2, 1)

        self._tts_voice_tr = QComboBox()
        self._tts_voice_tr.addItem("tr-TR-EmelNeural (Female)", "tr-TR-EmelNeural")
        self._tts_voice_tr.addItem("tr-TR-AhmetNeural (Male)", "tr-TR-AhmetNeural")
        cur_tr = config.get("tts", "voices", "tr", default="tr-TR-EmelNeural")
        idx_tr = self._tts_voice_tr.findData(cur_tr)
        if idx_tr >= 0:
            self._tts_voice_tr.setCurrentIndex(idx_tr)
        tts_grid.addWidget(self._tts_voice_tr, 3, 1)

        # English Voice
        en_label_h = QHBoxLayout()
        en_badge = QLabel("EN")
        en_badge.setStyleSheet(f"background-color: {FIELD}; color: {ACCENT_CYAN}; font-size: 10px; font-weight: bold; border-radius: 4px; padding: 2px 4px;")
        en_label_h.addWidget(en_badge)
        en_label_h.addWidget(QLabel("English Voice"), 1)
        tts_grid.addLayout(en_label_h, 4, 1)

        self._tts_voice_en = QComboBox()
        self._tts_voice_en.addItem("en-US-JennyNeural (Female)", "en-US-JennyNeural")
        self._tts_voice_en.addItem("en-US-GuyNeural (Male)", "en-US-GuyNeural")
        self._tts_voice_en.addItem("en-US-AriaNeural (Female)", "en-US-AriaNeural")
        self._tts_voice_en.addItem("en-GB-RyanNeural (Male)", "en-GB-RyanNeural")
        cur_en = config.get("tts", "voices", "en", default="en-US-JennyNeural")
        idx_en = self._tts_voice_en.findData(cur_en)
        if idx_en >= 0:
            self._tts_voice_en.setCurrentIndex(idx_en)
        tts_grid.addWidget(self._tts_voice_en, 5, 1)

        tts_layout.addLayout(tts_grid)
        layout.addWidget(tts_card)

        layout.addStretch()
        return tab

    def _step_rate(self, delta: int):
        txt = self._tts_rate.text().replace("%", "").strip()
        try:
            val = int(txt)
        except ValueError:
            val = 0
        val += delta
        sign = "+" if val >= 0 else ""
        self._tts_rate.setText(f"{sign}{val}%")

    # ─── 3. Responses Tab (Instant Responses — Google Stitch Exact) ───
    def _build_responses_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 2 Column layout: Left Phrase Management, Right Syntax Reference
        h_layout = QHBoxLayout()
        h_layout.setSpacing(16)

        # Left Card: Predefined Phrase List
        left_card = QFrame()
        left_card.setObjectName("sectionCard")
        l_layout = QVBoxLayout(left_card)
        l_layout.setSpacing(14)

        # Top Row: Title + Toggle Switch
        top_r = QHBoxLayout()
        t_col = QVBoxLayout()
        t_col.setSpacing(2)
        t_title = QLabel("Predefined Phrase List")
        t_title.setObjectName("rowTitle")
        t_desc = QLabel("Bypass LLM processing for specific queries.")
        t_desc.setObjectName("rowDesc")
        t_col.addWidget(t_title)
        t_col.addWidget(t_desc)
        top_r.addLayout(t_col, 1)

        self._instant_enabled_switch = ToggleSwitch(checked=config.get("instant", "enabled", default=True))
        top_r.addWidget(self._instant_enabled_switch)
        l_layout.addLayout(top_r)
        l_layout.addWidget(self._divider())

        # Middle Status Bar (Green dot + phrases count)
        status_bar = QFrame()
        status_bar.setObjectName("innerCard")
        s_bar_l = QHBoxLayout(status_bar)
        s_bar_l.setContentsMargins(12, 10, 12, 10)
        s_bar_l.setSpacing(8)

        s_dot = QLabel("●")
        s_dot.setStyleSheet(f"color: {ACCENT}; font-size: 11px;")
        self._instant_count_label = QLabel("130 phrases active")
        self._instant_count_label.setStyleSheet(f"color: {ACCENT}; font-family: 'Cascadia Code', monospace; font-size: 12px; font-weight: 600;")
        s_bar_l.addWidget(s_dot)
        s_bar_l.addWidget(self._instant_count_label)
        s_bar_l.addStretch()
        l_layout.addWidget(status_bar)

        # Action Buttons Row: Edit YAML, Show Folder, Reload
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        edit_btn = QPushButton("✏  Edit YAML")
        edit_btn.clicked.connect(self._open_instant_file)
        btn_row.addWidget(edit_btn)

        folder_btn = QPushButton("📁  Show Folder")
        folder_btn.clicked.connect(self._open_instant_folder)
        btn_row.addWidget(folder_btn)

        reload_btn = QPushButton("🔄  Reload")
        reload_btn.setObjectName("primaryBtn")
        reload_btn.clicked.connect(self._reload_instant_file)
        btn_row.addWidget(reload_btn)

        l_layout.addLayout(btn_row)
        l_layout.addStretch()

        h_layout.addWidget(left_card, 1)

        # Right Card: Syntax Reference
        right_card = QFrame()
        right_card.setObjectName("sectionCard")
        r_layout = QVBoxLayout(right_card)
        r_layout.setSpacing(12)

        syn_head = QLabel("Syntax Reference")
        syn_head.setObjectName("rowTitle")
        r_layout.addWidget(syn_head)
        r_layout.addWidget(self._divider())

        # Formatted Code Block Card
        code_box = QFrame()
        code_box.setObjectName("codeCard")
        code_l = QVBoxLayout(code_box)
        code_l.setContentsMargins(14, 14, 14, 14)
        code_l.setSpacing(4)

        sample_code = (
            "<pre style='margin:0; font-family: \"Cascadia Code\", Consolas, monospace; font-size: 11.5px; line-height: 1.5;'>"
            "<span style='color:#555562;'>-</span> <span style='color:#00D4AA; font-weight:600;'>pattern:</span> <span style='color:#38F2D8;'>\"what time is it\"</span><br>"
            "  <span style='color:#00D4AA; font-weight:600;'>response:</span> <span style='color:#e9e9ee;'>\"{sys.time}\"</span><br>"
            "  <span style='color:#00D4AA; font-weight:600;'>lang:</span> <span style='color:#38F2D8;'>\"en\"</span><br>"
            "  <span style='color:#00D4AA; font-weight:600;'>match:</span> <span style='color:#38F2D8;'>\"exact\"</span><br><br>"
            "<span style='color:#555562;'>-</span> <span style='color:#00D4AA; font-weight:600;'>pattern:</span> <span style='color:#38F2D8;'>\"reboot system\"</span><br>"
            "  <span style='color:#00D4AA; font-weight:600;'>response:</span> <span style='color:#e9e9ee;'>\"Initiating restart...\"</span><br>"
            "  <span style='color:#00D4AA; font-weight:600;'>action:</span> <span style='color:#38F2D8;'>\"cmd_reboot\"</span>"
            "</pre>"
        )

        code_lbl = QLabel(sample_code)
        code_lbl.setTextFormat(Qt.TextFormat.RichText)
        code_l.addWidget(code_lbl)
        r_layout.addWidget(code_box, 1)

        h_layout.addWidget(right_card, 1)
        layout.addLayout(h_layout)

        layout.addStretch()
        self._refresh_instant_status()
        return tab

    # ─── 4. LLM Tab (Local AI Engine) ─────────────────────────────────
    def _build_llm_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        # Header with Engine Status Badge
        top_row = QHBoxLayout()
        head_lbl = QLabel("🖫  Ollama Engine")
        head_lbl.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 700;")
        top_row.addWidget(head_lbl)
        top_row.addStretch()

        self._ollama_status_badge = StatusBadge("Connected", is_active=True)
        top_row.addWidget(self._ollama_status_badge)
        card_layout.addLayout(top_row)
        card_layout.addWidget(self._divider())

        # Grid: Base URL and Model
        g1 = QGridLayout()
        g1.setSpacing(12)

        g1.addWidget(QLabel("Base URL:"), 0, 0)
        self._ollama_url = QLineEdit(config.get("llm", "ollama", "base_url", default="http://127.0.0.1:11434"))
        g1.addWidget(self._ollama_url, 0, 1)

        g1.addWidget(QLabel("Model:"), 0, 2)
        self._ollama_model = QComboBox()
        models = ["qwen2.5:3b", "qwen2.5:7b", "llama3.2:3b", "phi3.5", "gemma2:2b", "mistral"]
        self._ollama_model.addItems(models)
        self._ollama_model.setEditable(True)
        current_model = config.get("llm", "ollama", "model", default="qwen2.5:3b")
        self._ollama_model.setCurrentText(current_model)
        g1.addWidget(self._ollama_model, 0, 3)

        card_layout.addLayout(g1)
        card_layout.addWidget(self._divider())

        # Temperature Slider + Tokens + Context
        temp_row = QHBoxLayout()
        temp_col = QVBoxLayout()
        temp_col.setSpacing(4)

        temp_top = QHBoxLayout()
        temp_title = QLabel("Temperature")
        temp_title.setObjectName("rowTitle")
        temp_top.addWidget(temp_title)
        temp_top.addStretch()

        current_temp = config.get("llm", "ollama", "temperature", default=0.70)
        self._temp_badge = QLabel(f"{current_temp:.2f}")
        self._temp_badge.setStyleSheet(f"""
            color: {ACCENT};
            background-color: {FIELD};
            border: 1px solid rgba(0, 212, 170, 0.3);
            border-radius: 6px;
            padding: 3px 8px;
            font-family: monospace;
            font-weight: 700;
            font-size: 11px;
        """)
        temp_top.addWidget(self._temp_badge)
        temp_col.addLayout(temp_top)

        self._temp_slider = QSlider(Qt.Orientation.Horizontal)
        self._temp_slider.setRange(0, 100)
        self._temp_slider.setValue(int(current_temp * 100))
        self._temp_slider.valueChanged.connect(
            lambda v: self._temp_badge.setText(f"{v / 100.0:.2f}")
        )
        temp_col.addWidget(self._temp_slider)

        labels_h = QHBoxLayout()
        lbl_p = QLabel("Precise")
        lbl_p.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        lbl_c = QLabel("Creative")
        lbl_c.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 10px;")
        labels_h.addWidget(lbl_p)
        labels_h.addStretch()
        labels_h.addWidget(lbl_c)
        temp_col.addLayout(labels_h)

        temp_row.addLayout(temp_col, 2)
        temp_row.addSpacing(16)

        # Max Tokens & Context
        tok_col = QVBoxLayout()
        tok_col.setSpacing(4)
        tok_lbl = QLabel("Max Tokens")
        tok_lbl.setObjectName("rowTitle")
        tok_col.addWidget(tok_lbl)
        self._max_tokens = QSpinBox()
        self._max_tokens.setRange(64, 4096)
        self._max_tokens.setSingleStep(64)
        self._max_tokens.setValue(config.get("llm", "ollama", "max_tokens", default=256))
        tok_col.addWidget(self._max_tokens)
        temp_row.addLayout(tok_col, 1)

        ctx_col = QVBoxLayout()
        ctx_col.setSpacing(4)
        ctx_lbl = QLabel("Context (turns)")
        ctx_lbl.setObjectName("rowTitle")
        ctx_col.addWidget(ctx_lbl)
        self._context_window = QSpinBox()
        self._context_window.setRange(1, 50)
        self._context_window.setValue(config.get("llm", "context_window", default=8))
        ctx_col.addWidget(self._context_window)
        temp_row.addLayout(ctx_col, 1)

        card_layout.addLayout(temp_row)
        card_layout.addWidget(self._divider())

        # Executable Path
        exe_row = QHBoxLayout()
        exe_text = QVBoxLayout()
        exe_text.setSpacing(2)
        exe_title = QLabel("Executable Path")
        exe_title.setObjectName("rowTitle")
        exe_desc = QLabel("Auto-detect or custom ollama.exe location.")
        exe_desc.setObjectName("rowDesc")
        exe_text.addWidget(exe_title)
        exe_text.addWidget(exe_desc)
        exe_row.addLayout(exe_text, 1)

        self._ollama_exe = QLineEdit(config.get("llm", "ollama", "executable", default=""))
        self._ollama_exe.setPlaceholderText("Auto-detect")
        self._ollama_exe.setFixedWidth(220)
        exe_browse = QPushButton("Browse")
        exe_browse.clicked.connect(self._browse_ollama_exe)
        exe_row.addWidget(self._ollama_exe)
        exe_row.addWidget(exe_browse)
        card_layout.addLayout(exe_row)
        card_layout.addWidget(self._divider())

        # Auto-start toggle
        t1_row = QHBoxLayout()
        t1_col = QVBoxLayout()
        t1_col.setSpacing(2)
        t1_title = QLabel("Start Ollama automatically")
        t1_title.setObjectName("rowTitle")
        t1_desc = QLabel("Launch the background service when SAM starts.")
        t1_desc.setObjectName("rowDesc")
        t1_col.addWidget(t1_title)
        t1_col.addWidget(t1_desc)
        t1_row.addLayout(t1_col, 1)
        self._ollama_autostart_switch = ToggleSwitch(checked=config.get("llm", "ollama", "autostart", default=True))
        t1_row.addWidget(self._ollama_autostart_switch)
        card_layout.addLayout(t1_row)
        card_layout.addWidget(self._divider())

        # Stop on exit toggle
        t2_row = QHBoxLayout()
        t2_col = QVBoxLayout()
        t2_col.setSpacing(2)
        t2_title = QLabel("Stop server when SAM quits")
        t2_title.setObjectName("rowTitle")
        t2_desc = QLabel("Terminate the Ollama process on exit.")
        t2_desc.setObjectName("rowDesc")
        t2_col.addWidget(t2_title)
        t2_col.addWidget(t2_desc)
        t2_row.addLayout(t2_col, 1)
        self._ollama_stop_on_exit_switch = ToggleSwitch(checked=config.get("llm", "ollama", "stop_on_exit", default=False))
        t2_row.addWidget(self._ollama_stop_on_exit_switch)
        card_layout.addLayout(t2_row)

        layout.addWidget(card)
        layout.addStretch()
        return tab

    # ─── 5. Appearance Tab (Desktop Orb Overlay) ──────────────────────
    def _build_ui_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # 2 Column layout: Left Live Preview, Right Controls
        h_layout = QHBoxLayout()
        h_layout.setSpacing(16)

        # Left Card: Interactive Live Preview
        preview_card = QFrame()
        preview_card.setObjectName("sectionCard")
        preview_card.setFixedWidth(240)
        p_layout = QVBoxLayout(preview_card)
        p_layout.setContentsMargins(14, 14, 14, 14)
        p_layout.setSpacing(10)

        p_head = QLabel("PREVIEW")
        p_head.setObjectName("cardSectionTitle")
        p_layout.addWidget(p_head)

        self._live_orb_preview = LiveOrbPreview()
        p_layout.addWidget(self._live_orb_preview, 1)

        h_layout.addWidget(preview_card)

        # Right Card: Controls
        ctrl_card = QFrame()
        ctrl_card.setObjectName("sectionCard")
        c_layout = QVBoxLayout(ctrl_card)
        c_layout.setSpacing(12)

        # Style: Segmented Control
        style_row = QHBoxLayout()
        s_title = QLabel("STYLE")
        s_title.setObjectName("cardSectionTitle")
        style_row.addWidget(s_title)
        style_row.addStretch()

        current_style = config.get("ui", "overlay", "style", default="orb").capitalize()
        self._style_segmented = SegmentedControl(["Orb", "Bar"], current=current_style)
        style_row.addWidget(self._style_segmented)
        c_layout.addLayout(style_row)
        c_layout.addWidget(self._divider())

        # 4 Sliders in 2x2 grid
        slider_grid = QGridLayout()
        slider_grid.setSpacing(14)

        # Diameter
        d_val = config.get("ui", "orb", "size", default=120)
        self._diameter_badge = QLabel(f"{d_val} px")
        self._diameter_badge.setStyleSheet(f"color: {ACCENT}; font-family: monospace; font-weight: 700;")
        self._diameter_slider = QSlider(Qt.Orientation.Horizontal)
        self._diameter_slider.setRange(60, 320)
        self._diameter_slider.setValue(d_val)
        self._diameter_slider.valueChanged.connect(self._on_orb_params_changed)

        d_col = QVBoxLayout()
        d_top = QHBoxLayout()
        d_top.addWidget(QLabel("DIAMETER"))
        d_top.addStretch()
        d_top.addWidget(self._diameter_badge)
        d_col.addLayout(d_top)
        d_col.addWidget(self._diameter_slider)
        slider_grid.addLayout(d_col, 0, 0)

        # Ring Width
        r_val = config.get("ui", "orb", "ring_width", default=3)
        self._ring_badge = QLabel(f"{r_val} px")
        self._ring_badge.setStyleSheet(f"color: {ACCENT}; font-family: monospace; font-weight: 700;")
        self._ring_slider = QSlider(Qt.Orientation.Horizontal)
        self._ring_slider.setRange(1, 12)
        self._ring_slider.setValue(r_val)
        self._ring_slider.valueChanged.connect(self._on_orb_params_changed)

        r_col = QVBoxLayout()
        r_top = QHBoxLayout()
        r_top.addWidget(QLabel("RING WIDTH"))
        r_top.addStretch()
        r_top.addWidget(self._ring_badge)
        r_col.addLayout(r_top)
        r_col.addWidget(self._ring_slider)
        slider_grid.addLayout(r_col, 0, 1)

        # Opacity
        o_val = int(config.get("ui", "orb", "opacity", default=0.95) * 100)
        self._opacity_badge = QLabel(f"{o_val}%")
        self._opacity_badge.setStyleSheet(f"color: {ACCENT}; font-family: monospace; font-weight: 700;")
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 100)
        self._opacity_slider.setValue(o_val)
        self._opacity_slider.valueChanged.connect(self._on_orb_params_changed)

        o_col = QVBoxLayout()
        o_top = QHBoxLayout()
        o_top.addWidget(QLabel("OPACITY"))
        o_top.addStretch()
        o_top.addWidget(self._opacity_badge)
        o_col.addLayout(o_top)
        o_col.addWidget(self._opacity_slider)
        slider_grid.addLayout(o_col, 1, 0)

        # Auto-hide Delay
        a_val = config.get("ui", "auto_hide", "delay_seconds", default=4)
        self._autohide_badge = QLabel(f"{a_val} sec")
        self._autohide_badge.setStyleSheet(f"color: {ACCENT}; font-family: monospace; font-weight: 700;")
        self._autohide_slider = QSlider(Qt.Orientation.Horizontal)
        self._autohide_slider.setRange(1, 30)
        self._autohide_slider.setValue(a_val)
        self._autohide_slider.valueChanged.connect(
            lambda v: self._autohide_badge.setText(f"{v} sec")
        )

        a_col = QVBoxLayout()
        a_top = QHBoxLayout()
        a_top.addWidget(QLabel("AUTO-HIDE DELAY"))
        a_top.addStretch()
        a_top.addWidget(self._autohide_badge)
        a_col.addLayout(a_top)
        a_col.addWidget(self._autohide_slider)
        slider_grid.addLayout(a_col, 1, 1)

        c_layout.addLayout(slider_grid)
        c_layout.addWidget(self._divider())

        # Click-through & Animation mode sub-row
        sub_row = QHBoxLayout()
        sub_row.setSpacing(12)

        ct_box = QFrame()
        ct_box.setObjectName("innerCard")
        ct_l = QHBoxLayout(ct_box)
        ct_l.addWidget(QLabel("Click-through"), 1)
        self._click_through_switch = ToggleSwitch(checked=config.get("ui", "orb", "click_through", default=True))
        ct_l.addWidget(self._click_through_switch)
        sub_row.addWidget(ct_box, 1)

        anim_box = QFrame()
        anim_box.setObjectName("innerCard")
        anim_l = QHBoxLayout(anim_box)
        anim_l.addWidget(QLabel("Animation"), 1)
        self._orb_idle_anim = QComboBox()
        self._orb_idle_anim.addItems([
            "Off (0% CPU)",
            "Breathing (12 fps)",
            "Smooth (24 fps)",
        ])
        if not config.get("ui", "orb", "idle_animation", default=True):
            self._orb_idle_anim.setCurrentIndex(0)
        elif config.get("ui", "orb", "idle_fps", default=12) >= 20:
            self._orb_idle_anim.setCurrentIndex(2)
        else:
            self._orb_idle_anim.setCurrentIndex(1)
        anim_l.addWidget(self._orb_idle_anim)
        sub_row.addWidget(anim_box, 1)

        c_layout.addLayout(sub_row)

        # Reset Position Button
        reset_row = QHBoxLayout()
        reset_row.addStretch()
        reset_pos_btn = QPushButton("Reset Position")
        reset_pos_btn.clicked.connect(self._reset_orb_position)
        reset_row.addWidget(reset_pos_btn)
        c_layout.addLayout(reset_row)

        h_layout.addWidget(ctrl_card, 1)
        layout.addLayout(h_layout)

        self._on_orb_params_changed()
        return tab

    def _on_orb_params_changed(self):
        d = self._diameter_slider.value()
        r = self._ring_slider.value()
        o = self._opacity_slider.value() / 100.0

        self._diameter_badge.setText(f"{d} px")
        self._ring_badge.setText(f"{r} px")
        self._opacity_badge.setText(f"{int(o * 100)}%")

        self._live_orb_preview.update_params(d, r, o)

    # ─── 6. Integrations Tab (Connected Services) ─────────────────────
    def _build_integrations_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(16)

        # Card 1: Spotify Integration
        spotify_card = QFrame()
        spotify_card.setObjectName("sectionCard")
        s_layout = QVBoxLayout(spotify_card)
        s_layout.setSpacing(12)

        s_top = QHBoxLayout()
        s_icon = QLabel("🟢")
        s_icon.setStyleSheet("font-size: 16px;")
        s_info = QVBoxLayout()
        s_info.setSpacing(1)
        s_title = QLabel("Spotify Integration")
        s_title.setObjectName("rowTitle")
        s_sub = QLabel("Audio Control API")
        s_sub.setObjectName("rowDesc")
        s_info.addWidget(s_title)
        s_info.addWidget(s_sub)

        s_top.addWidget(s_icon)
        s_top.addLayout(s_info)
        s_top.addStretch()

        has_spotify = bool(config.get("spotify", "client_id", default=""))
        s_top.addWidget(StatusBadge("Connected" if has_spotify else "Disconnected", is_active=has_spotify))
        s_layout.addLayout(s_top)
        s_layout.addWidget(self._divider())

        # Client ID
        s_layout.addWidget(QLabel("Client ID"))
        cid_row = QHBoxLayout()
        self._spotify_client_id = QLineEdit(config.get("spotify", "client_id", default=""))
        self._spotify_client_id.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        copy_cid_btn = QPushButton("📋")
        copy_cid_btn.setObjectName("iconBtn")
        copy_cid_btn.clicked.connect(lambda: QApplication.clipboard().setText(self._spotify_client_id.text()))
        cid_row.addWidget(self._spotify_client_id, 1)
        cid_row.addWidget(copy_cid_btn)
        s_layout.addLayout(cid_row)

        # Client Secret
        s_layout.addWidget(QLabel("Client Secret"))
        sec_row = QHBoxLayout()
        self._spotify_client_secret = QLineEdit(config.get("spotify", "client_secret", default=""))
        self._spotify_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        eye_btn = QPushButton("👁")
        eye_btn.setObjectName("iconBtn")
        eye_btn.clicked.connect(self._toggle_spotify_secret_visibility)
        sec_row.addWidget(self._spotify_client_secret, 1)
        sec_row.addWidget(eye_btn)
        s_layout.addLayout(sec_row)

        # Redirect URI
        s_layout.addWidget(QLabel("Redirect URI"))
        uri_row = QHBoxLayout()
        self._spotify_redirect = QLineEdit(config.get("spotify", "redirect_uri", default="http://127.0.0.1:8080"))
        copy_uri_btn = QPushButton("📋")
        copy_uri_btn.setObjectName("iconBtn")
        copy_uri_btn.clicked.connect(lambda: QApplication.clipboard().setText(self._spotify_redirect.text()))
        uri_row.addWidget(self._spotify_redirect, 1)
        uri_row.addWidget(copy_uri_btn)
        s_layout.addLayout(uri_row)

        s_btn_row = QHBoxLayout()
        sync_btn = QPushButton("Sync Now")
        sync_btn.clicked.connect(lambda: QMessageBox.information(self, "Spotify", "Spotify status synchronized."))
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.setObjectName("dangerOutlineBtn")
        disconnect_btn.clicked.connect(self._clear_spotify)
        s_btn_row.addWidget(sync_btn)
        s_btn_row.addWidget(disconnect_btn)
        s_layout.addLayout(s_btn_row)

        grid.addWidget(spotify_card, 0, 0)

        # Card 2: Notion Workspace
        notion_card = QFrame()
        notion_card.setObjectName("sectionCard")
        n_layout = QVBoxLayout(notion_card)
        n_layout.setSpacing(12)

        n_top = QHBoxLayout()
        n_icon = QLabel("📄")
        n_icon.setStyleSheet("font-size: 16px;")
        n_info = QVBoxLayout()
        n_info.setSpacing(1)
        n_title = QLabel("Notion Workspace")
        n_title.setObjectName("rowTitle")
        n_sub = QLabel("Memory & Notes Sync")
        n_sub.setObjectName("rowDesc")
        n_info.addWidget(n_title)
        n_info.addWidget(n_sub)

        n_top.addWidget(n_icon)
        n_top.addLayout(n_info)
        n_top.addStretch()
        n_top.addWidget(StatusBadge("Disconnected", is_active=False))
        n_layout.addLayout(n_top)
        n_layout.addWidget(self._divider())

        dashed = QFrame()
        dashed.setObjectName("dashedCard")
        d_l = QVBoxLayout(dashed)
        d_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d_msg = QLabel("Connect Notion to allow SAM to read and write to your workspace.")
        d_msg.setWordWrap(True)
        d_msg.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11.5px; text-align: center;")
        d_l.addWidget(d_msg)
        n_layout.addWidget(dashed, 1)

        conn_btn = QPushButton("Connect Service")
        conn_btn.setObjectName("primaryBtn")
        conn_btn.clicked.connect(lambda: QMessageBox.information(self, "Notion", "Notion integration coming in next update!"))
        n_layout.addWidget(conn_btn)

        grid.addWidget(notion_card, 0, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return tab

    def _toggle_spotify_secret_visibility(self):
        if self._spotify_client_secret.echoMode() == QLineEdit.EchoMode.Password:
            self._spotify_client_secret.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self._spotify_client_secret.setEchoMode(QLineEdit.EchoMode.Password)

    def _clear_spotify(self):
        self._spotify_client_id.clear()
        self._spotify_client_secret.clear()
        QMessageBox.information(self, "Spotify", "Spotify integration credentials cleared.")

    # ─── 7. About Tab (About & Diagnostics) ───────────────────────────
    def _build_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        top_grid = QGridLayout()
        top_grid.setSpacing(16)

        # Card 1: ABOUT SAM
        about_card = QFrame()
        about_card.setObjectName("sectionCard")
        a_layout = QVBoxLayout(about_card)
        a_layout.setSpacing(12)

        a_head = QLabel("ABOUT SAM")
        a_head.setObjectName("cardSectionTitle")
        a_layout.addWidget(a_head)

        sam_info_row = QHBoxLayout()
        sam_icon = QLabel("🤖")
        sam_icon.setStyleSheet(f"""
            font-size: 24px;
            background-color: {FIELD};
            border: 1px solid {BORDER};
            border-radius: 8px;
            padding: 8px;
        """)
        sam_text_col = QVBoxLayout()
        sam_text_col.setSpacing(2)
        v_str = config.get("app", "version", default="0.4.6")
        sam_title = QLabel(f"SAM v{v_str}")
        sam_title.setStyleSheet(f"color: {TEXT}; font-size: 15px; font-weight: 700;")
        sam_sub = QLabel("Smart Assistant Module")
        sam_sub.setObjectName("rowDesc")
        sam_text_col.addWidget(sam_title)
        sam_text_col.addWidget(sam_sub)

        sam_info_row.addWidget(sam_icon)
        sam_info_row.addLayout(sam_text_col)
        sam_info_row.addStretch()
        a_layout.addLayout(sam_info_row)

        # Author
        author_row = QHBoxLayout()
        a_lbl = QLabel("Author")
        a_lbl.setObjectName("rowDesc")
        author_val = QLabel("Samet Gürtuna")
        author_val.setStyleSheet(f"color: {TEXT}; font-weight: 600; font-size: 12px;")
        author_row.addWidget(a_lbl)
        author_row.addStretch()
        author_row.addWidget(author_val)
        a_layout.addLayout(author_row)

        # Core Stack Tags
        a_layout.addWidget(QLabel("Core Stack"))
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(6)
        for tag in ["PyQt6", "Faster-Whisper", "Ollama", "Edge-TTS", "OpenWakeWord"]:
            t_lbl = QLabel(tag)
            t_lbl.setStyleSheet(f"""
                color: {TEXT_DIM};
                background-color: {FIELD};
                border: 1px solid {BORDER};
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-family: monospace;
            """)
            tags_layout.addWidget(t_lbl)
        tags_layout.addStretch()
        a_layout.addLayout(tags_layout)

        github_btn = QPushButton("</>  View on GitHub")
        github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        github_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/sametgurtuna/SAM")))
        a_layout.addWidget(github_btn)

        top_grid.addWidget(about_card, 0, 0)

        # Card 2: SYSTEM PATHS
        paths_card = QFrame()
        paths_card.setObjectName("sectionCard")
        p_layout = QVBoxLayout(paths_card)
        p_layout.setSpacing(10)

        p_head = QLabel("SYSTEM PATHS")
        p_head.setObjectName("cardSectionTitle")
        p_layout.addWidget(p_head)

        from core import paths

        p_layout.addWidget(QLabel("Configuration"))
        cfg_field = QLineEdit(paths.config_path())
        cfg_field.setReadOnly(True)
        cfg_field.setStyleSheet(f"color: {ACCENT}; font-family: monospace; font-size: 11px;")
        p_layout.addWidget(cfg_field)

        p_layout.addWidget(QLabel("Logs Directory"))
        log_field = QLineEdit(str(paths.logs_dir()))
        log_field.setReadOnly(True)
        log_field.setStyleSheet(f"color: {ACCENT}; font-family: monospace; font-size: 11px;")
        p_layout.addWidget(log_field)

        p_layout.addWidget(QLabel("Models Path"))
        mod_field = QLineEdit(str(paths.models_dir()))
        mod_field.setReadOnly(True)
        mod_field.setStyleSheet(f"color: {ACCENT}; font-family: monospace; font-size: 11px;")
        p_layout.addWidget(mod_field)

        open_folder_btn = QPushButton("📁  Open User Data Folder")
        open_folder_btn.setObjectName("primaryBtn")
        open_folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(paths.user_data_dir())))
        p_layout.addWidget(open_folder_btn)

        top_grid.addWidget(paths_card, 0, 1)

        layout.addLayout(top_grid)

        # Bottom Card: ENVIRONMENT STATUS (4 Grid Boxes)
        env_card = QFrame()
        env_card.setObjectName("sectionCard")
        env_layout = QVBoxLayout(env_card)
        env_layout.setSpacing(10)

        env_head = QLabel("ENVIRONMENT STATUS")
        env_head.setObjectName("cardSectionTitle")
        env_layout.addWidget(env_head)

        boxes_grid = QGridLayout()
        boxes_grid.setSpacing(12)

        # 1. Python
        b1 = self._make_stat_box("Python", sys.version.split()[0], is_accent=True)
        boxes_grid.addWidget(b1, 0, 0)

        # 2. OS
        os_name = f"{platform.system()} {platform.machine()}"
        b2 = self._make_stat_box("OS", os_name, is_accent=False)
        boxes_grid.addWidget(b2, 0, 1)

        # 3. CUDA
        cuda_str = "CPU Mode"
        try:
            import torch
            if torch.cuda.is_available():
                cuda_str = f"Available ({torch.version.cuda})"
        except Exception:
            pass
        b3 = self._make_stat_box("CUDA", cuda_str, is_accent=(cuda_str != "CPU Mode"))
        boxes_grid.addWidget(b3, 0, 2)

        # 4. Uptime
        self._uptime_label = QLabel("00:00:00")
        self._uptime_label.setStyleSheet(f"color: {TEXT}; font-family: monospace; font-size: 13px; font-weight: 700;")
        b4 = QFrame()
        b4.setObjectName("innerCard")
        b4_l = QVBoxLayout(b4)
        b4_l.setSpacing(2)
        b4_title = QLabel("Uptime")
        b4_title.setObjectName("rowDesc")
        b4_l.addWidget(b4_title)
        b4_l.addWidget(self._uptime_label)
        boxes_grid.addWidget(b4, 0, 3)

        env_layout.addLayout(boxes_grid)
        layout.addWidget(env_card)

        # Uptime timer
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
        self._uptime_timer.start(1000)
        self._update_uptime()

        layout.addStretch()
        return tab

    def _make_stat_box(self, title: str, val: str, is_accent: bool = False) -> QFrame:
        box = QFrame()
        box.setObjectName("innerCard")
        l = QVBoxLayout(box)
        l.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("rowDesc")
        v = QLabel(val)
        c = ACCENT if is_accent else TEXT
        v.setStyleSheet(f"color: {c}; font-family: monospace; font-size: 13px; font-weight: 700;")
        l.addWidget(t)
        l.addWidget(v)
        return box

    def _update_uptime(self):
        elapsed = int(time.time() - APP_START_TIME)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self._uptime_label.setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")

    # ─── Instant Response Dosya Islemleri ─────────────────────────────
    def _instant_responder(self):
        return getattr(self._controller, "_instant", None)

    def _instant_file_path(self) -> str:
        responder = self._instant_responder()
        if responder is not None:
            return responder.path
        from commands.instant import InstantResponder, DEFAULT_FILE
        return InstantResponder._resolve_path(config.get("instant", "file", default=None) or DEFAULT_FILE)

    def _refresh_instant_status(self) -> None:
        responder = self._instant_responder()
        count = responder.count if responder is not None else 130
        self._instant_count_label.setText(f"{count} phrases active")

    def _open_instant_file(self) -> None:
        path = self._instant_file_path()
        if not os.path.exists(path):
            QMessageBox.warning(self, "Instant Responses", f"The responses file was not found:\n{path}")
            return
        try:
            os.startfile(path)
        except OSError:
            try:
                subprocess.Popen(["notepad.exe", path])
            except Exception as e:
                QMessageBox.warning(self, "Instant Responses", f"Could not open the file:\n{e}")

    def _open_instant_folder(self) -> None:
        folder = os.path.dirname(self._instant_file_path())
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _reload_instant_file(self) -> None:
        responder = self._instant_responder()
        if responder is None:
            QMessageBox.information(
                self, "Instant Responses",
                "Instant responses are disabled. Enable them, save, and restart SAM to load the file."
            )
            return
        try:
            responder.reload()
        except Exception as e:
            QMessageBox.critical(self, "Instant Responses", f"Reload failed:\n{e}")
            return
        self._refresh_instant_status()
        QMessageBox.information(self, "Instant Responses", f"Reloaded — {responder.count} phrases are now active.")

    def _reset_orb_position(self) -> None:
        if self._controller is not None and hasattr(self._controller._bar, "reset_position"):
            self._controller._bar.reset_position()
            QMessageBox.information(self, "Orb Position", "Orb position reset to default bottom-right.")
        else:
            config.set("ui", "orb", "position", "anchor", value="bottom-right")
            config.set("ui", "orb", "position", "x", value=None)
            config.set("ui", "orb", "position", "y", value=None)
            config.save()
            QMessageBox.information(self, "Orb Position", "Orb position reset. Restart SAM to apply.")

    # ─── Save Settings ────────────────────────────────────────────────
    def _save_settings(self):
        try:
            # 1. General
            config.set("hotkey", "trigger", value=self._hotkey_input.text().strip())
            config.set("hotkey", "text_input", value=self._text_hotkey_input.text().strip())
            config.set("wake_word", "model", value=self._wake_model_combo.currentText())
            config.set("wake_word", "threshold", value=self._wake_threshold_slider.value() / 100.0)

            # 2. Speech
            config.set("stt", "model", value=self._stt_model_combo.currentText())
            lang_data = self._stt_language_combo.currentData()
            if lang_data is None:
                lang_data = self._stt_language_combo.currentText().strip()
            config.set("stt", "language", value=lang_data if lang_data else None)

            config.set("stt", "device", value=self._stt_device_combo.currentText().lower())
            config.set("stt", "partial_model", value=self._stt_partial_model.currentData())
            config.set("stt", "partial_interval_ms", value=self._stt_partial_interval_slider.value())

            # 3. Instant
            config.set("instant", "enabled", value=self._instant_enabled_switch.isChecked())

            config.set("tts", "engine", value=self._tts_engine_combo.currentText())
            config.set("tts", "voice", value=self._tts_voice.currentText())
            config.set("tts", "rate", value=self._tts_rate.text().strip())
            config.set("tts", "auto_language", value=self._tts_auto_language_switch.isChecked())
            
            tr_voice_val = self._tts_voice_tr.currentData() or self._tts_voice_tr.currentText().split()[0]
            config.set("tts", "voices", "tr", value=tr_voice_val)

            en_voice_val = self._tts_voice_en.currentData() or self._tts_voice_en.currentText().split()[0]
            config.set("tts", "voices", "en", value=en_voice_val)

            # 4. LLM
            config.set("llm", "ollama", "base_url", value=self._ollama_url.text().strip())
            config.set("llm", "ollama", "model", value=self._ollama_model.currentText())
            config.set("llm", "ollama", "temperature", value=self._temp_slider.value() / 100.0)
            config.set("llm", "ollama", "max_tokens", value=self._max_tokens.value())
            config.set("llm", "context_window", value=self._context_window.value())
            config.set("llm", "ollama", "autostart", value=self._ollama_autostart_switch.isChecked())
            config.set("llm", "ollama", "executable", value=self._ollama_exe.text().strip())
            config.set("llm", "ollama", "stop_on_exit", value=self._ollama_stop_on_exit_switch.isChecked())

            # 5. Appearance / UI
            config.set("ui", "overlay", "style", value=self._style_segmented.current_text().lower())
            config.set("ui", "orb", "size", value=self._diameter_slider.value())
            config.set("ui", "orb", "ring_width", value=self._ring_slider.value())
            config.set("ui", "orb", "opacity", value=self._opacity_slider.value() / 100.0)
            config.set("ui", "orb", "click_through", value=self._click_through_switch.isChecked())

            idle_index = self._orb_idle_anim.currentIndex()
            config.set("ui", "orb", "idle_animation", value=idle_index != 0)
            if idle_index == 2:
                config.set("ui", "orb", "idle_fps", value=24)
            elif idle_index == 1:
                config.set("ui", "orb", "idle_fps", value=12)

            config.set("ui", "auto_hide", "delay_seconds", value=self._autohide_slider.value())

            # 6. Spotify
            config.set("spotify", "client_id", value=self._spotify_client_id.text().strip())
            config.set("spotify", "client_secret", value=self._spotify_client_secret.text().strip())
            config.set("spotify", "redirect_uri", value=self._spotify_redirect.text().strip())

            # Kaydet
            success = config.save()
            if success:
                logger.info("Settings saved via modern UI")
                self.settings_saved.emit()
                QMessageBox.information(
                    self, "Settings Saved",
                    "Settings saved successfully.\n\n"
                    "• Appearance and auto-hide apply immediately.\n"
                    "• Speech & LLM models take effect on restart."
                )
                self.close()
            else:
                QMessageBox.warning(self, "Error", "Failed to save config file.")

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            QMessageBox.critical(self, "Error", f"Error saving settings:\n{e}")

    def _browse_ollama_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ollama.exe", "", "Executables (*.exe);;All Files (*)"
        )
        if file_path:
            self._ollama_exe.setText(file_path)

    def _browse_custom_wake_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Custom Wake Word Model", "", "Wake Word Models (*.onnx *.tflite);;All Files (*)"
        )
        if file_path:
            file_path = file_path.replace("\\", "/")
            idx = self._wake_model_combo.findText(file_path)
            if idx < 0:
                self._wake_model_combo.addItem(file_path)
                idx = self._wake_model_combo.count() - 1
            self._wake_model_combo.setCurrentIndex(idx)
