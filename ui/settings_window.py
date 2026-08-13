# SAM — Settings Window
# Modern sidebar-based settings window. config.yaml degerlerini GUI uzerinden
# duzenlemeyi ve kaydetmeyi saglar. Premium koyu tema tasarimi.

import logging
import os
import subprocess

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QListWidget, QStackedWidget,
    QLabel, QLineEdit, QComboBox, QSlider, QSpinBox, QPushButton,
    QGroupBox, QDoubleSpinBox, QMessageBox, QWidget, QFileDialog, QCheckBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices

from core.config import config

logger = logging.getLogger(__name__)

# ─── Tema ─────────────────────────────────────────────────────────
# Renkler orb/overlay ile ayni paletten: koyu zemin + tek vurgu (teal).
ACCENT = "#00D4AA"
ACCENT_SOFT = "rgba(0, 212, 170, 0.14)"
BG = "#0a0a0f"
SURFACE = "#101018"
SURFACE_HI = "#16161f"
FIELD = "#1a1a24"
BORDER = "rgba(255, 255, 255, 0.07)"
TEXT = "#e9e9ee"
TEXT_DIM = "#8b8b97"

SETTINGS_STYLESHEET = f"""
QDialog {{
    background-color: {BG};
    color: {TEXT};
}}
QWidget {{
    font-family: "Segoe UI";
}}

/* ─── Sidebar ─────────────────────────────────────────────── */
QListWidget#sidebar {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    outline: none;
    padding: 8px 6px;
    font-size: 13px;
}}
QListWidget#sidebar::item {{
    color: {TEXT_DIM};
    padding: 11px 14px;
    border-radius: 8px;
    margin: 2px 0;
}}
QListWidget#sidebar::item:hover {{
    background-color: {SURFACE_HI};
    color: {TEXT};
}}
QListWidget#sidebar::item:selected {{
    background-color: {ACCENT_SOFT};
    color: {ACCENT};
    font-weight: 600;
}}

/* ─── Basliklar ───────────────────────────────────────────── */
QLabel#appTitle {{
    color: {TEXT};
    font-size: 19px;
    font-weight: 700;
}}
QLabel#appSubtitle {{
    color: {TEXT_DIM};
    font-size: 12px;
}}
QLabel#versionPill {{
    color: {ACCENT};
    background-color: {ACCENT_SOFT};
    border: 1px solid rgba(0, 212, 170, 0.25);
    border-radius: 10px;
    padding: 3px 12px;
    font-size: 11px;
    font-weight: 600;
}}
QLabel#pageTitle {{
    color: {TEXT};
    font-size: 16px;
    font-weight: 600;
}}
QLabel#pageDesc {{
    color: {TEXT_DIM};
    font-size: 12px;
}}
QLabel#hint {{
    color: {TEXT_DIM};
    font-size: 11px;
}}
QWidget#page, QWidget#pageViewport {{
    background: transparent;
}}
QFrame#divider {{
    background-color: {BORDER};
    max-height: 1px;
    border: none;
}}

/* ─── Kartlar (QGroupBox) ─────────────────────────────────── */
QGroupBox {{
    font-size: 12px;
    font-weight: 600;
    color: {ACCENT};
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 12px;
    padding: 30px 16px 16px 16px;
    background-color: {SURFACE};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: 4px;
    padding: 0 2px;
}}

/* ─── Girdiler ────────────────────────────────────────────── */
QLabel {{
    color: #c3c3cd;
    font-size: 12px;
}}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: {TEXT};
    padding: 7px 11px;
    font-size: 12px;
    min-height: 20px;
    selection-background-color: {ACCENT};
    selection-color: {BG};
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: rgba(255, 255, 255, 0.16);
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
    background-color: {SURFACE_HI};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    color: #55555f;
    background-color: #14141c;
}}
QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
/* down-arrow'a dokunmuyoruz: Qt'nin yerel oku CSS ucgen hilesinden daha
   duzgun ciziliyor, "image: none" verilince kare bir kutuya donusuyor. */
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

/* ─── Onay kutulari ───────────────────────────────────────── */
QCheckBox {{
    color: #c3c3cd;
    font-size: 12px;
    spacing: 9px;
}}
QCheckBox::indicator {{
    width: 17px;
    height: 17px;
    border-radius: 5px;
    border: 1px solid rgba(255, 255, 255, 0.18);
    background-color: {FIELD};
}}
QCheckBox::indicator:hover {{
    border-color: {ACCENT};
}}
QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ─── Kaydiriciler ────────────────────────────────────────── */
QSlider::groove:horizontal {{
    height: 5px;
    background: #23232f;
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 15px;
    height: 15px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::handle:horizontal:hover {{
    background: #00ffcc;
}}
QSlider::sub-page:horizontal {{
    background: rgba(0, 212, 170, 0.55);
    border-radius: 3px;
}}

/* ─── Butonlar ────────────────────────────────────────────── */
QPushButton {{
    background-color: {FIELD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 500;
    min-width: 88px;
}}
QPushButton:hover {{
    background-color: #23232f;
    border-color: rgba(255, 255, 255, 0.18);
}}
QPushButton:pressed {{
    background-color: #1c1c26;
}}
QPushButton#primary {{
    background-color: {ACCENT};
    color: {BG};
    border: none;
    font-weight: 700;
}}
QPushButton#primary:hover {{
    background-color: #16f5ce;
}}
QPushButton#linkButton {{
    background: transparent;
    border: none;
    color: {ACCENT};
    text-align: left;
    padding: 2px 0;
    min-width: 0;
    font-size: 12px;
}}
QPushButton#linkButton:hover {{
    color: #16f5ce;
    text-decoration: underline;
}}

/* ─── Kaydirma cubugu ─────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #2a2a38;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #3a3a4c;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QToolTip {{
    background-color: {SURFACE_HI};
    color: {TEXT};
    border: 1px solid rgba(0, 212, 170, 0.3);
    border-radius: 6px;
    padding: 6px 9px;
    font-size: 11px;
}}
"""

class SettingsWindow(QDialog):
    """
    SAM Settings penceresi.
    Modern sidebar layout uzerinden ayarlari duzenler.
    """

    # Ayarlar kaydedildi — controller ucuz anahtarlari restart'siz uygular.
    settings_saved = pyqtSignal()

    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self._controller = controller
        self.setWindowTitle("SAM — Settings")
        # Sabit boyut yerine makul bir varsayilan + alt sinir: kullanici
        # pencereyi buyutebilsin, kucuk ekranlarda da sigsin.
        self.resize(880, 660)
        self.setMinimumSize(760, 560)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(22, 20, 22, 18)

        main_layout.addLayout(self._build_header())
        main_layout.addWidget(self._divider())

        # Icerik alani (Sidebar + Stack)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(18)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(186)
        self.sidebar.currentRowChanged.connect(self._change_page)
        content_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        main_layout.addLayout(content_layout, 1)

        # Sayfalar
        self._add_page(
            "⚡  General", "General",
            "How SAM wakes up and starts listening.",
            self._build_general_tab(),
        )
        self._add_page(
            "🎙  Speech", "Speech",
            "Transcription accuracy vs. speed, and the voice SAM answers in.",
            self._build_speech_tab(),
        )
        self._add_page(
            "💬  Responses", "Instant Responses",
            "Phrases SAM answers immediately — these never reach the LLM.",
            self._build_responses_tab(),
        )
        self._add_page(
            "🧠  LLM", "Language Model",
            "The local Ollama engine used for everything else.",
            self._build_llm_tab(),
        )
        self._add_page(
            "🎨  Appearance", "Appearance",
            "The orb overlay — size, placement and idle cost.",
            self._build_ui_tab(),
        )
        self._add_page(
            "🎵  Integrations", "Integrations",
            "External services SAM can control on your behalf.",
            self._build_integrations_tab(),
        )
        self._add_page(
            "ℹ  About", "About",
            "Version and project information.",
            self._build_about_tab(),
        )

        self.sidebar.setCurrentRow(0)

        main_layout.addWidget(self._divider())

        # Alt bar
        footer_layout = QHBoxLayout()
        hint = QLabel("Appearance and auto-hide apply instantly — other changes need a restart.")
        hint.setObjectName("hint")
        footer_layout.addWidget(hint)
        footer_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        footer_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primary")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save_settings)
        footer_layout.addWidget(save_btn)

        main_layout.addLayout(footer_layout)

    # ─── Iskelet yardimcilari ─────────────────────────────────────

    def _build_header(self) -> QHBoxLayout:
        version = config.get("app", "version", default="0.4.6")

        text_col = QVBoxLayout()
        text_col.setSpacing(1)
        title = QLabel("SAM Settings")
        title.setObjectName("appTitle")
        subtitle = QLabel("Smart Assistant Module")
        subtitle.setObjectName("appSubtitle")
        text_col.addWidget(title)
        text_col.addWidget(subtitle)

        pill = QLabel(f"v{version}")
        pill.setObjectName("versionPill")

        header = QHBoxLayout()
        header.addLayout(text_col)
        header.addStretch()
        header.addWidget(pill, 0, Qt.AlignmentFlag.AlignVCenter)
        return header

    @staticmethod
    def _divider() -> QFrame:
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        return line

    def _add_page(self, nav_label: str, title: str, description: str, widget: QWidget):
        """Sayfayi baslik + aciklama ile sarip sidebar'a kaydet."""
        page = QWidget()
        page.setObjectName("page")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(2)

        heading = QLabel(title)
        heading.setObjectName("pageTitle")
        desc = QLabel(description)
        desc.setObjectName("pageDesc")
        desc.setWordWrap(True)
        page_layout.addWidget(heading)
        page_layout.addWidget(desc)
        page_layout.addSpacing(6)
        page_layout.addWidget(widget, 1)

        # Sayfalar kaydirilabilir: yeni ayar eklendiginde icerik pencereden
        # tasip kirpilmasin.
        scroll = QScrollArea()
        scroll.setWidget(page)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        # Selector'suz bir stylesheet ("background: transparent;") viewport'un
        # TUM alt widget'larina miras kalir ve butonlarin kendi arka planini
        # eziyordu (Reload butonu gorunmez oluyordu). Sadece viewport'u hedefle.
        scroll.viewport().setObjectName("pageViewport")

        self.sidebar.addItem(nav_label)
        self.stack.addWidget(scroll)

    @staticmethod
    def _note(text: str) -> QLabel:
        """Bir kart icindeki aciklama satiri."""
        label = QLabel(text)
        label.setObjectName("pageDesc")
        label.setWordWrap(True)
        return label

    def _change_page(self, index: int):
        self.stack.setCurrentIndex(index)

    # ─── General Tab ──────────────────────────────────────────────

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        hotkey_group = QGroupBox("Activation")
        form = QFormLayout()
        form.setSpacing(12)

        self._hotkey_input = QLineEdit(config.get("hotkey", "trigger", default="ctrl+space"))
        form.addRow("Voice Hotkey:", self._hotkey_input)

        self._text_hotkey_input = QLineEdit(
            config.get("hotkey", "text_input", default="ctrl+shift+space")
        )
        self._text_hotkey_input.setToolTip(
            "Opens the typed-input box under the orb. Clicking the orb does the same."
        )
        form.addRow("Text Hotkey:", self._text_hotkey_input)

        self._wake_model_combo = QComboBox()
        wake_models = ["assets/models/hey_sam.onnx", "hey_jarvis", "alexa", "hey_mycroft", "ok_google"]
        current_wake = config.get("wake_word", "model", default="assets/models/hey_sam.onnx")
        if current_wake not in wake_models:
            wake_models.append(current_wake)
        self._wake_model_combo.addItems(wake_models)
        idx = self._wake_model_combo.findText(current_wake)
        if idx >= 0:
            self._wake_model_combo.setCurrentIndex(idx)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_custom_wake_model)
        
        wake_layout = QHBoxLayout()
        wake_layout.addWidget(self._wake_model_combo, 1)
        wake_layout.addWidget(browse_btn)
        form.addRow("Wake Word:", wake_layout)

        self._wake_threshold = QDoubleSpinBox()
        self._wake_threshold.setRange(0.1, 1.0)
        self._wake_threshold.setSingleStep(0.05)
        self._wake_threshold.setValue(config.get("wake_word", "threshold", default=0.5))
        form.addRow("Wake Threshold:", self._wake_threshold)

        hotkey_group.setLayout(form)
        layout.addWidget(hotkey_group)
        layout.addStretch()
        return tab

    # ─── Speech Tab ───────────────────────────────────────────────

    def _build_speech_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        stt_group = QGroupBox("Speech-to-Text (Whisper)")
        form = QFormLayout()
        form.setSpacing(12)

        self._stt_model_combo = QComboBox()
        stt_models = ["tiny", "base", "small", "medium", "large-v3"]
        self._stt_model_combo.addItems(stt_models)
        current_stt = config.get("stt", "model", default="base")
        idx = self._stt_model_combo.findText(current_stt)
        if idx >= 0:
            self._stt_model_combo.setCurrentIndex(idx)
        form.addRow("Model:", self._stt_model_combo)

        # None = otomatik dil algilama (varsayilan) — QLineEdit None kabul
        # etmedigi icin bos string'e cevir.
        self._stt_language = QLineEdit(config.get("stt", "language", default=None) or "")
        self._stt_language.setPlaceholderText("en, tr, de, fr... (empty = auto)")
        form.addRow("Language:", self._stt_language)

        self._stt_model_combo.setToolTip(
            "Bigger is more accurate but slower. This model runs once, after you "
            "stop speaking."
        )

        self._stt_device_combo = QComboBox()
        self._stt_device_combo.addItems(["cpu", "cuda"])
        current_device = config.get("stt", "device", default="cpu")
        idx = self._stt_device_combo.findText(current_device)
        if idx >= 0:
            self._stt_device_combo.setCurrentIndex(idx)
        form.addRow("Device:", self._stt_device_combo)

        stt_group.setLayout(form)
        layout.addWidget(stt_group)

        # ─── Canli transkripsiyon ─────────────────────────────────
        live_group = QGroupBox("Live Transcription")
        form_live = QFormLayout()
        form_live.setSpacing(12)
        form_live.addRow(self._note(
            "A second, smaller model transcribes while you are still speaking, so "
            "you see words appear in real time. Known commands are also dispatched "
            "from it — they never wait for the main model."
        ))

        self._stt_partial_model = QComboBox()
        for label, value in (
            ("tiny — fastest", "tiny"),
            ("base — recommended", "base"),
            ("small — most accurate", "small"),
            ("same as main model", ""),
            ("off — no live text", "off"),
        ):
            self._stt_partial_model.addItem(label, value)
        current_partial = config.get("stt", "partial_model", default="base")
        idx = self._stt_partial_model.findData(current_partial)
        self._stt_partial_model.setCurrentIndex(idx if idx >= 0 else 1)
        form_live.addRow("Live Model:", self._stt_partial_model)

        self._stt_partial_interval = QSpinBox()
        self._stt_partial_interval.setRange(150, 2000)
        self._stt_partial_interval.setSingleStep(50)
        self._stt_partial_interval.setSuffix(" ms")
        self._stt_partial_interval.setValue(
            config.get("stt", "partial_interval_ms", default=400)
        )
        self._stt_partial_interval.setToolTip(
            "Minimum gap between two live decodes. Lower feels snappier but uses "
            "more CPU."
        )
        form_live.addRow("Refresh Every:", self._stt_partial_interval)

        live_group.setLayout(form_live)
        layout.addWidget(live_group)

        tts_group = QGroupBox("Text-to-Speech")
        form2 = QFormLayout()
        form2.setSpacing(12)

        self._tts_engine_combo = QComboBox()
        self._tts_engine_combo.addItems(["edge-tts", "local"])
        current_engine = config.get("tts", "engine", default="edge-tts")
        idx_engine = self._tts_engine_combo.findText(current_engine)
        if idx_engine >= 0:
            self._tts_engine_combo.setCurrentIndex(idx_engine)
        form2.addRow("Engine:", self._tts_engine_combo)

        self._tts_voice = QComboBox()
        voices = [
            "en-US-GuyNeural", "en-US-JennyNeural", "en-US-AriaNeural",
            "en-GB-RyanNeural", "en-GB-SoniaNeural",
            "tr-TR-AhmetNeural", "tr-TR-EmelNeural",
        ]
        self._tts_voice.addItems(voices)
        self._tts_voice.setEditable(True)
        current_voice = config.get("tts", "voice", default="en-US-GuyNeural")
        self._tts_voice.setCurrentText(current_voice)
        form2.addRow("Fallback voice:", self._tts_voice)

        self._tts_rate = QLineEdit(config.get("tts", "rate", default="+0%"))
        self._tts_rate.setPlaceholderText("+0%, +20%, -10%")
        form2.addRow("Rate:", self._tts_rate)

        self._tts_auto_language = QCheckBox(
            "Switch voice automatically to match the language you spoke in"
        )
        self._tts_auto_language.setChecked(
            config.get("tts", "auto_language", default=True)
        )
        form2.addRow(self._tts_auto_language)

        self._tts_voice_tr = QComboBox()
        self._tts_voice_tr.addItems(voices)
        self._tts_voice_tr.setEditable(True)
        self._tts_voice_tr.setCurrentText(
            config.get("tts", "voices", "tr", default="tr-TR-EmelNeural")
        )
        form2.addRow("Turkish voice:", self._tts_voice_tr)

        self._tts_voice_en = QComboBox()
        self._tts_voice_en.addItems(voices)
        self._tts_voice_en.setEditable(True)
        self._tts_voice_en.setCurrentText(
            config.get("tts", "voices", "en", default="en-US-JennyNeural")
        )
        form2.addRow("English voice:", self._tts_voice_en)

        tts_group.setLayout(form2)
        layout.addWidget(tts_group)
        layout.addStretch()
        return tab

    # ─── Instant Responses Tab ────────────────────────────────────

    def _build_responses_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        group = QGroupBox("Phrase List")
        form = QVBoxLayout()
        form.setSpacing(12)

        form.addWidget(self._note(
            "SAM keeps a list of phrases it answers straight away — greetings, "
            "thanks, the time, questions about itself. A match is spoken in "
            "milliseconds and never reaches the language model."
        ))

        self._instant_enabled = QCheckBox("Answer predefined phrases instantly")
        self._instant_enabled.setChecked(config.get("instant", "enabled", default=True))
        form.addWidget(self._instant_enabled)

        # Dosya yolu — kullanicinin duzenleyecegi kopya
        self._instant_path_label = QLabel()
        self._instant_path_label.setObjectName("pageDesc")
        self._instant_path_label.setWordWrap(True)
        self._instant_path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addWidget(self._instant_path_label)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton("Edit Responses…")
        edit_btn.setToolTip("Opens the YAML file in your default text editor")
        edit_btn.clicked.connect(self._open_instant_file)
        btn_row.addWidget(edit_btn)

        folder_btn = QPushButton("Show Folder")
        folder_btn.clicked.connect(self._open_instant_folder)
        btn_row.addWidget(folder_btn)

        reload_btn = QPushButton("Reload")
        reload_btn.setObjectName("primary")
        reload_btn.setToolTip("Apply your edits without restarting SAM")
        reload_btn.clicked.connect(self._reload_instant_file)
        btn_row.addWidget(reload_btn)
        btn_row.addStretch()
        form.addLayout(btn_row)

        form.addWidget(self._note(
            "Format — each entry needs <b>patterns</b> (what you say) and "
            "<b>response</b> (a line, or a list to pick from at random). "
            "Optional: <b>lang: tr|en</b> for the voice and for the "
            "{time} / {date} / {day} placeholders, and <b>match: contains</b> to "
            "match anywhere in the sentence. Casing, punctuation and Turkish "
            "accents are ignored. Hit Reload after saving."
        ))

        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch()

        self._refresh_instant_status()
        return tab

    # ─── Instant response dosya islemleri ─────────────────────────

    def _instant_responder(self):
        """Calisan InstantResponder — controller yoksa None."""
        return getattr(self._controller, "_instant", None)

    def _instant_file_path(self) -> str:
        responder = self._instant_responder()
        if responder is not None:
            return responder.path

        # Instant kapaliyken de dosya yolunu gosterebilmek icin: ayni cozumleme.
        from commands.instant import InstantResponder, DEFAULT_FILE
        return InstantResponder._resolve_path(
            config.get("instant", "file", default=None) or DEFAULT_FILE
        )

    def _refresh_instant_status(self) -> None:
        path = self._instant_file_path()
        responder = self._instant_responder()
        count = responder.count if responder is not None else 0
        loaded = f"{count} phrase{'s' if count != 1 else ''} loaded — " if count else ""
        self._instant_path_label.setText(f"{loaded}{path}")

    def _open_instant_file(self) -> None:
        path = self._instant_file_path()
        if not os.path.exists(path):
            QMessageBox.warning(
                self, "Instant Responses",
                f"The responses file was not found:\n{path}"
            )
            return
        # Varsayilan .yaml uygulamasi olmayabilir — startfile basarisiz olursa
        # Not Defteri'ne dus.
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except OSError:
            try:
                subprocess.Popen(["notepad.exe", path])
            except Exception as e:
                QMessageBox.warning(self, "Instant Responses",
                                    f"Could not open the file:\n{e}")

    def _open_instant_folder(self) -> None:
        folder = os.path.dirname(self._instant_file_path())
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _reload_instant_file(self) -> None:
        responder = self._instant_responder()
        if responder is None:
            QMessageBox.information(
                self, "Instant Responses",
                "Instant responses are disabled. Enable them, save, and restart "
                "SAM to load the file."
            )
            return
        try:
            responder.reload()
        except Exception as e:
            QMessageBox.critical(self, "Instant Responses", f"Reload failed:\n{e}")
            return
        self._refresh_instant_status()
        QMessageBox.information(
            self, "Instant Responses",
            f"Reloaded — {responder.count} phrases are now active."
        )

    # ─── LLM Tab ──────────────────────────────────────────────────

    def _build_llm_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        ollama_group = QGroupBox("Ollama (Local)")
        form = QFormLayout()
        form.setSpacing(12)

        self._ollama_url = QLineEdit(
            config.get("llm", "ollama", "base_url", default="http://127.0.0.1:11434")
        )
        form.addRow("Base URL:", self._ollama_url)

        self._ollama_model = QComboBox()
        models = ["qwen2.5:3b", "qwen2.5:7b", "llama3.2:3b", "phi3.5", "gemma2:2b", "mistral"]
        self._ollama_model.addItems(models)
        self._ollama_model.setEditable(True)
        current_model = config.get("llm", "ollama", "model", default="qwen2.5:3b")
        self._ollama_model.setCurrentText(current_model)
        form.addRow("Model:", self._ollama_model)

        temp_layout = QHBoxLayout()
        self._temp_slider = QSlider(Qt.Orientation.Horizontal)
        self._temp_slider.setRange(0, 100)
        current_temp = config.get("llm", "ollama", "temperature", default=0.7)
        self._temp_slider.setValue(int(current_temp * 100))
        self._temp_label = QLabel(f"{current_temp:.2f}")
        self._temp_label.setFixedWidth(36)
        self._temp_slider.valueChanged.connect(
            lambda v: self._temp_label.setText(f"{v / 100:.2f}")
        )
        temp_layout.addWidget(self._temp_slider)
        temp_layout.addWidget(self._temp_label)
        form.addRow("Temperature:", temp_layout)

        self._max_tokens = QSpinBox()
        self._max_tokens.setRange(64, 4096)
        self._max_tokens.setSingleStep(64)
        self._max_tokens.setValue(config.get("llm", "ollama", "max_tokens", default=256))
        form.addRow("Max Tokens:", self._max_tokens)

        self._context_window = QSpinBox()
        self._context_window.setRange(1, 50)
        self._context_window.setValue(config.get("llm", "context_window", default=5))
        form.addRow("Context Window:", self._context_window)

        self._ollama_autostart = QCheckBox("Start the Ollama server when SAM launches")
        self._ollama_autostart.setChecked(
            config.get("llm", "ollama", "autostart", default=True)
        )
        form.addRow("Auto-start:", self._ollama_autostart)

        exe_layout = QHBoxLayout()
        self._ollama_exe = QLineEdit(config.get("llm", "ollama", "executable", default=""))
        self._ollama_exe.setPlaceholderText("Auto-detect (leave blank)")
        exe_browse = QPushButton("Browse...")
        exe_browse.clicked.connect(self._browse_ollama_exe)
        exe_layout.addWidget(self._ollama_exe, 1)
        exe_layout.addWidget(exe_browse)
        form.addRow("Executable:", exe_layout)

        self._ollama_stop_on_exit = QCheckBox("Stop the server when SAM quits")
        self._ollama_stop_on_exit.setToolTip(
            "Only applies to a server SAM started itself. Off by default so a "
            "server you were already using is never killed."
        )
        self._ollama_stop_on_exit.setChecked(
            config.get("llm", "ollama", "stop_on_exit", default=False)
        )
        form.addRow("", self._ollama_stop_on_exit)

        ollama_group.setLayout(form)
        layout.addWidget(ollama_group)
        layout.addStretch()
        return tab

    # ─── UI Tab ───────────────────────────────────────────────────

    def _build_ui_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        orb_group = QGroupBox("Orb")
        form = QFormLayout()
        form.setSpacing(12)

        self._overlay_style = QComboBox()
        self._overlay_style.addItems(["orb", "bar"])
        idx = self._overlay_style.findText(
            config.get("ui", "overlay", "style", default="orb")
        )
        if idx >= 0:
            self._overlay_style.setCurrentIndex(idx)
        form.addRow("Overlay Style:", self._overlay_style)

        self._orb_size = QSpinBox()
        self._orb_size.setRange(60, 320)
        self._orb_size.setSingleStep(10)
        self._orb_size.setSuffix(" px")
        self._orb_size.setValue(config.get("ui", "orb", "size", default=120))
        form.addRow("Size:", self._orb_size)

        self._orb_ring_width = QSpinBox()
        self._orb_ring_width.setRange(1, 12)
        self._orb_ring_width.setSuffix(" px")
        self._orb_ring_width.setValue(config.get("ui", "orb", "ring_width", default=3))
        form.addRow("Ring Width:", self._orb_ring_width)

        opacity_layout = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 100)
        current_opacity = config.get("ui", "orb", "opacity", default=0.95)
        self._opacity_slider.setValue(int(current_opacity * 100))
        self._opacity_label = QLabel(f"{current_opacity:.2f}")
        self._opacity_label.setFixedWidth(36)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v / 100:.2f}")
        )
        opacity_layout.addWidget(self._opacity_slider)
        opacity_layout.addWidget(self._opacity_label)
        form.addRow("Opacity:", opacity_layout)

        # SAM 7/24 arkaplanda calisiyor — idle animasyon maliyeti onemli.
        self._orb_idle_anim = QComboBox()
        self._orb_idle_anim.addItems([
            "Off (0% CPU when idle)",
            "Breathing (12 fps)",
            "Smooth (24 fps)",
        ])
        if not config.get("ui", "orb", "idle_animation", default=True):
            self._orb_idle_anim.setCurrentIndex(0)
        elif config.get("ui", "orb", "idle_fps", default=12) >= 20:
            self._orb_idle_anim.setCurrentIndex(2)
        else:
            self._orb_idle_anim.setCurrentIndex(1)
        form.addRow("Idle Animation:", self._orb_idle_anim)

        self._orb_click_through = QCheckBox("Mouse passes through (except the circle)")
        self._orb_click_through.setChecked(
            config.get("ui", "orb", "click_through", default=True)
        )
        form.addRow("Click-through:", self._orb_click_through)

        self._orb_layer = QComboBox()
        self._orb_layer.addItems(["auto", "topmost", "normal"])
        self._orb_layer.setToolTip(
            "auto: stays at the bottom, only comes to front when SAM is called\n"
            "topmost: always on top of every window\n"
            "normal: no special stacking behavior"
        )
        idx = self._orb_layer.findText(config.get("ui", "orb", "layer", default="auto"))
        if idx >= 0:
            self._orb_layer.setCurrentIndex(idx)
        form.addRow("Layer:", self._orb_layer)

        self._orb_hide_fullscreen = QCheckBox("Hide during fullscreen apps")
        self._orb_hide_fullscreen.setChecked(
            config.get("ui", "orb", "hide_on_fullscreen", default=True)
        )
        form.addRow("", self._orb_hide_fullscreen)

        self._caption_width = QSpinBox()
        self._caption_width.setRange(280, 1400)
        self._caption_width.setSingleStep(20)
        self._caption_width.setSuffix(" px")
        self._caption_width.setValue(config.get("ui", "orb", "caption_width", default=560))
        form.addRow("Caption Width:", self._caption_width)

        self._auto_hide = QSpinBox()
        self._auto_hide.setRange(1, 30)
        self._auto_hide.setSuffix(" sec")
        self._auto_hide.setValue(config.get("ui", "auto_hide", "delay_seconds", default=4))
        form.addRow("Auto-hide Delay:", self._auto_hide)

        reset_pos_btn = QPushButton("Reset Orb Position")
        reset_pos_btn.clicked.connect(self._reset_orb_position)
        form.addRow("", reset_pos_btn)

        orb_group.setLayout(form)
        layout.addWidget(orb_group)
        layout.addStretch()
        return tab

    def _reset_orb_position(self) -> None:
        """Snap the orb back to its default corner (Ctrl+drag moves it)."""
        if self._controller is not None and hasattr(self._controller._bar, "reset_position"):
            self._controller._bar.reset_position()
            QMessageBox.information(self, "Orb Position", "Orb position reset.")
        else:
            config.set("ui", "orb", "position", "anchor", value="bottom-right")
            config.set("ui", "orb", "position", "x", value=None)
            config.set("ui", "orb", "position", "y", value=None)
            config.save()
            QMessageBox.information(
                self, "Orb Position", "Orb position reset. Restart SAM to apply."
            )

    # ─── Integrations (Spotify) Tab ───────────────────────────────

    def _build_integrations_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        spotify_group = QGroupBox("Spotify API Integration")
        form = QFormLayout()
        form.setSpacing(12)

        info_label = QLabel("Connect SAM to Spotify for direct audio control.\\nGet your keys from developer.spotify.com")
        info_label.setStyleSheet("color: #888; font-size: 11px;")
        form.addRow(info_label)

        self._spotify_client_id = QLineEdit(config.get("spotify", "client_id", default=""))
        self._spotify_client_id.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        form.addRow("Client ID:", self._spotify_client_id)

        self._spotify_client_secret = QLineEdit(config.get("spotify", "client_secret", default=""))
        self._spotify_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Client Secret:", self._spotify_client_secret)

        self._spotify_redirect = QLineEdit(config.get("spotify", "redirect_uri", default="http://localhost:8080"))
        form.addRow("Redirect URI:", self._spotify_redirect)

        spotify_group.setLayout(form)
        layout.addWidget(spotify_group)
        layout.addStretch()
        return tab

    # ─── About Tab ────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        version = config.get("app", "version", default="0.4.6")

        card = QGroupBox("SAM")
        card_layout = QVBoxLayout()
        card_layout.setSpacing(8)

        card_layout.addWidget(self._note(
            f"<span style='color:#e9e9ee; font-size:14px;'>Smart Assistant Module "
            f"<b>v{version}</b></span><br>"
            "A privacy-first desktop voice assistant. Speech recognition and the "
            "language model both run on your own machine — nothing is sent to the "
            "cloud unless you configure it to."
        ))

        card_layout.addWidget(self._note(
            "Built by <b>Samet Gürtuna</b><br>"
            "Powered by PyQt6 · faster-whisper · Ollama · edge-tts"
        ))

        repo_btn = QPushButton("View the project on GitHub  ↗")
        repo_btn.setObjectName("linkButton")
        repo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        repo_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://github.com/sametgurtuna/SAM")
        ))
        card_layout.addWidget(repo_btn, 0, Qt.AlignmentFlag.AlignLeft)

        card.setLayout(card_layout)
        layout.addWidget(card)

        files_card = QGroupBox("Files")
        files_layout = QVBoxLayout()
        files_layout.setSpacing(8)

        from core import paths
        files_layout.addWidget(self._note(
            f"Configuration: {paths.config_path()}<br>"
            f"Logs: {paths.logs_dir()}<br>"
            f"Models: {paths.models_dir()}"
        ))

        folder_btn = QPushButton("Open Data Folder")
        folder_btn.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl.fromLocalFile(paths.user_data_dir())
        ))
        files_layout.addWidget(folder_btn, 0, Qt.AlignmentFlag.AlignLeft)

        files_card.setLayout(files_layout)
        layout.addWidget(files_card)
        layout.addStretch()
        return tab

    # ─── Save Logic ───────────────────────────────────────────────

    def _save_settings(self):
        """Tum widget degerlerini config'e yaz ve dosyaya kaydet."""
        try:
            # General
            config.set("hotkey", "trigger", value=self._hotkey_input.text().strip())
            config.set("hotkey", "text_input", value=self._text_hotkey_input.text().strip())
            config.set("wake_word", "model", value=self._wake_model_combo.currentText())
            config.set("wake_word", "threshold", value=self._wake_threshold.value())

            # Speech
            config.set("stt", "model", value=self._stt_model_combo.currentText())
            lang_val = self._stt_language.text().strip()
            config.set("stt", "language", value=lang_val if lang_val else None)
            config.set("stt", "device", value=self._stt_device_combo.currentText())
            config.set("stt", "partial_model",
                       value=self._stt_partial_model.currentData())
            config.set("stt", "partial_interval_ms",
                       value=self._stt_partial_interval.value())

            # Instant responses
            config.set("instant", "enabled", value=self._instant_enabled.isChecked())

            config.set("tts", "engine", value=self._tts_engine_combo.currentText())
            config.set("tts", "voice", value=self._tts_voice.currentText())
            config.set("tts", "rate", value=self._tts_rate.text().strip())
            config.set("tts", "auto_language", value=self._tts_auto_language.isChecked())
            config.set("tts", "voices", "tr", value=self._tts_voice_tr.currentText())
            config.set("tts", "voices", "en", value=self._tts_voice_en.currentText())

            # LLM
            config.set("llm", "ollama", "base_url", value=self._ollama_url.text().strip())
            config.set("llm", "ollama", "model", value=self._ollama_model.currentText())
            config.set("llm", "ollama", "temperature", value=self._temp_slider.value() / 100)
            config.set("llm", "ollama", "max_tokens", value=self._max_tokens.value())
            config.set("llm", "context_window", value=self._context_window.value())
            config.set("llm", "ollama", "autostart", value=self._ollama_autostart.isChecked())
            config.set("llm", "ollama", "executable", value=self._ollama_exe.text().strip())
            config.set("llm", "ollama", "stop_on_exit",
                       value=self._ollama_stop_on_exit.isChecked())

            # UI — Orb
            config.set("ui", "overlay", "style", value=self._overlay_style.currentText())
            config.set("ui", "orb", "size", value=self._orb_size.value())
            config.set("ui", "orb", "ring_width", value=self._orb_ring_width.value())
            config.set("ui", "orb", "opacity", value=self._opacity_slider.value() / 100)
            config.set("ui", "orb", "click_through",
                       value=self._orb_click_through.isChecked())
            config.set("ui", "orb", "layer", value=self._orb_layer.currentText())
            config.set("ui", "orb", "hide_on_fullscreen",
                       value=self._orb_hide_fullscreen.isChecked())
            config.set("ui", "orb", "caption_width", value=self._caption_width.value())

            idle_index = self._orb_idle_anim.currentIndex()
            config.set("ui", "orb", "idle_animation", value=idle_index != 0)
            if idle_index == 2:
                config.set("ui", "orb", "idle_fps", value=24)
            elif idle_index == 1:
                config.set("ui", "orb", "idle_fps", value=12)

            config.set("ui", "auto_hide", "delay_seconds", value=self._auto_hide.value())

            # Spotify
            config.set("spotify", "client_id", value=self._spotify_client_id.text().strip())
            config.set("spotify", "client_secret", value=self._spotify_client_secret.text().strip())
            config.set("spotify", "redirect_uri", value=self._spotify_redirect.text().strip())

            # Dosyaya kaydet
            success = config.save()

            if success:
                logger.info("Settings saved via UI")
                # Ucuz anahtarlar (orb boyutu/fps/opaklik/click-through,
                # auto-hide) restart'siz uygulanir.
                self.settings_saved.emit()
                QMessageBox.information(
                    self, "Settings Saved",
                    "Settings saved.\n\n"
                    "Orb appearance and auto-hide apply immediately.\n"
                    "Hotkeys, speech models and overlay style need a restart."
                )
                self.close()
            else:
                QMessageBox.warning(self, "Error", "Failed to save config file.")

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            QMessageBox.critical(self, "Error", f"Error saving settings:\n{e}")

    def _browse_ollama_exe(self):
        """Browse for the ollama executable."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select ollama.exe", "", "Executables (*.exe);;All Files (*)"
        )
        if file_path:
            self._ollama_exe.setText(file_path)

    def _browse_custom_wake_model(self):
        """Browse for custom openwakeword model file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Wake Word Model",
            "",
            "Wake Word Models (*.onnx *.tflite);;All Files (*)"
        )
        if file_path:
            # Mutlak yol olarak sakla. Eskiden CWD'ye gore goreli yapiliyordu,
            # ama SAM bir kisayoldan baslatildiginda CWD proje kokune esit
            # olmadigi icin model bulunamiyordu.
            file_path = file_path.replace("\\", "/")

            # Add file path to combo box if not present, and select it
            idx = self._wake_model_combo.findText(file_path)
            if idx < 0:
                self._wake_model_combo.addItem(file_path)
                idx = self._wake_model_combo.count() - 1
            self._wake_model_combo.setCurrentIndex(idx)
