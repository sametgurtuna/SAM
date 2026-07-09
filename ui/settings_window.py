# SAM — Settings Window
# Modern sidebar-based settings window. config.yaml degerlerini GUI uzerinden
# duzenlemeyi ve kaydetmeyi saglar. Premium koyu tema tasarimi.

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QListWidget, QStackedWidget,
    QLabel, QLineEdit, QComboBox, QSlider, QSpinBox, QPushButton,
    QGroupBox, QDoubleSpinBox, QMessageBox, QWidget, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.config import config

logger = logging.getLogger(__name__)

# ─── Premium Koyu Tema Stylesheet ─────────────────────────────────
SETTINGS_STYLESHEET = """
QDialog {
    background-color: #0b0b10;
    color: #e8e8e8;
}

/* Sidebar List */
QListWidget {
    background-color: #12121a;
    border: 1px solid rgba(0, 212, 170, 0.1);
    border-radius: 8px;
    outline: none;
    padding: 8px;
    font-size: 13px;
    font-weight: 500;
}
QListWidget::item {
    color: #a0a0a0;
    padding: 10px 14px;
    border-radius: 6px;
    margin-bottom: 4px;
}
QListWidget::item:hover {
    background-color: #18182a;
    color: #00D4AA;
}
QListWidget::item:selected {
    background-color: rgba(0, 212, 170, 0.1);
    color: #00D4AA;
    border-left: 3px solid #00D4AA;
    padding-left: 11px;
}

/* Content Area */
QStackedWidget {
    background-color: #0b0b10;
}

/* Group Boxes */
QGroupBox {
    font-size: 13px;
    font-weight: bold;
    color: #00D4AA;
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 24px;
    background-color: #12121a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 6px;
}

/* Inputs */
QLabel {
    color: #c8c8c8;
    font-size: 12px;
}
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #1a1a24;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    color: #e8e8e8;
    padding: 6px 10px;
    font-size: 12px;
    min-height: 20px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #00D4AA;
    background-color: #1c1c28;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1a1a24;
    color: #e8e8e8;
    selection-background-color: #00D4AA;
    selection-color: #0a0a0f;
    border: 1px solid rgba(0, 212, 170, 0.3);
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #242436;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #00D4AA;
    width: 14px;
    height: 14px;
    margin: -4px 0;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #00ffcc;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::sub-page:horizontal {
    background: rgba(0, 212, 170, 0.6);
    border-radius: 3px;
}

/* Buttons */
QPushButton {
    background-color: #1a1a24;
    color: #e8e8e8;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 8px 20px;
    font-size: 12px;
    font-weight: 500;
    min-width: 90px;
}
QPushButton:hover {
    background-color: #242436;
    border-color: rgba(255, 255, 255, 0.2);
}
QPushButton#saveButton {
    background-color: #00D4AA;
    color: #0b0b10;
    border: none;
    font-weight: bold;
}
QPushButton#saveButton:hover {
    background-color: #00ffcc;
}
"""

class SettingsWindow(QDialog):
    """
    SAM Settings penceresi.
    Modern sidebar layout uzerinden ayarlari duzenler.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SAM — Settings")
        self.setFixedSize(720, 560)
        self.setStyleSheet(SETTINGS_STYLESHEET)

        # Ana layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Baslik
        header_layout = QHBoxLayout()
        title = QLabel("⚙️ SAM Settings")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #00D4AA;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # Icerik alani (Sidebar + Stack)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(180)
        self.sidebar.currentRowChanged.connect(self._change_page)
        content_layout.addWidget(self.sidebar)

        # Stacked Widget (Sayfalar)
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack, 1)

        main_layout.addLayout(content_layout)

        # Sayfalari ekle
        self._add_page("⚡ General", self._build_general_tab())
        self._add_page("🎙️ Speech", self._build_speech_tab())
        self._add_page("🧠 LLM", self._build_llm_tab())
        self._add_page("🎨 UI", self._build_ui_tab())
        self._add_page("🎵 Integrations", self._build_integrations_tab())
        self._add_page("ℹ️ About", self._build_about_tab())

        # Ilk sayfayi sec
        self.sidebar.setCurrentRow(0)

        # Alt butonlar
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        footer_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("saveButton")
        save_btn.clicked.connect(self._save_settings)
        footer_layout.addWidget(save_btn)

        main_layout.addLayout(footer_layout)

    def _add_page(self, name: str, widget: QWidget):
        self.sidebar.addItem(name)
        self.stack.addWidget(widget)

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
        form.addRow("Hotkey:", self._hotkey_input)

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

        self._stt_language = QLineEdit(config.get("stt", "language", default="en"))
        self._stt_language.setPlaceholderText("en, tr, de, fr... (null = auto)")
        form.addRow("Language:", self._stt_language)

        self._stt_device_combo = QComboBox()
        self._stt_device_combo.addItems(["cpu", "cuda"])
        current_device = config.get("stt", "device", default="cpu")
        idx = self._stt_device_combo.findText(current_device)
        if idx >= 0:
            self._stt_device_combo.setCurrentIndex(idx)
        form.addRow("Device:", self._stt_device_combo)

        stt_group.setLayout(form)
        layout.addWidget(stt_group)

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
        form2.addRow("Voice:", self._tts_voice)

        self._tts_rate = QLineEdit(config.get("tts", "rate", default="+0%"))
        self._tts_rate.setPlaceholderText("+0%, +20%, -10%")
        form2.addRow("Rate:", self._tts_rate)

        tts_group.setLayout(form2)
        layout.addWidget(tts_group)
        layout.addStretch()
        return tab

    # ─── LLM Tab ──────────────────────────────────────────────────

    def _build_llm_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        ollama_group = QGroupBox("Ollama (Local)")
        form = QFormLayout()
        form.setSpacing(12)

        self._ollama_url = QLineEdit(
            config.get("llm", "ollama", "base_url", default="http://localhost:11434")
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

        ollama_group.setLayout(form)
        layout.addWidget(ollama_group)
        layout.addStretch()
        return tab

    # ─── UI Tab ───────────────────────────────────────────────────

    def _build_ui_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)

        bar_group = QGroupBox("Floating Bar")
        form = QFormLayout()
        form.setSpacing(12)

        self._bar_width = QSpinBox()
        self._bar_width.setRange(400, 1920)
        self._bar_width.setSingleStep(50)
        self._bar_width.setValue(config.get("ui", "bar", "width", default=800))
        form.addRow("Width (px):", self._bar_width)

        self._bar_height = QSpinBox()
        self._bar_height.setRange(40, 200)
        self._bar_height.setValue(config.get("ui", "bar", "height", default=80))
        form.addRow("Height (px):", self._bar_height)

        opacity_layout = QHBoxLayout()
        self._opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self._opacity_slider.setRange(30, 100)
        current_opacity = config.get("ui", "bar", "opacity", default=0.92)
        self._opacity_slider.setValue(int(current_opacity * 100))
        self._opacity_label = QLabel(f"{current_opacity:.2f}")
        self._opacity_label.setFixedWidth(36)
        self._opacity_slider.valueChanged.connect(
            lambda v: self._opacity_label.setText(f"{v / 100:.2f}")
        )
        opacity_layout.addWidget(self._opacity_slider)
        opacity_layout.addWidget(self._opacity_label)
        form.addRow("Opacity:", opacity_layout)

        self._auto_hide = QSpinBox()
        self._auto_hide.setRange(1, 30)
        self._auto_hide.setSuffix(" sec")
        self._auto_hide.setValue(config.get("ui", "auto_hide", "delay_seconds", default=4))
        form.addRow("Auto-hide Delay:", self._auto_hide)

        self._border_radius = QSpinBox()
        self._border_radius.setRange(0, 32)
        self._border_radius.setSuffix(" px")
        self._border_radius.setValue(config.get("ui", "bar", "border_radius", default=16))
        form.addRow("Border Radius:", self._border_radius)

        bar_group.setLayout(form)
        layout.addWidget(bar_group)
        layout.addStretch()
        return tab

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
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        version = config.get("app", "version", default="0.3.6")

        about_text = QLabel(
            f"<div style='text-align:center; padding: 20px;'>"
            f"<h2 style='color:#00D4AA; margin-bottom:4px;'>SAM</h2>"
            f"<p style='color:#888; font-size:13px;'>Smart Assistant Module</p>"
            f"<p style='color:#c8c8c8; font-size:14px;'>v{version}</p>"
            f"<br><br>"
            f"<p style='color:#888; font-size:12px;'>Privacy-first, offline-capable<br>"
            f"AI desktop voice assistant.</p>"
            f"<br><br>"
            f"<p style='color:#555; font-size:11px;'>"
            f"Developer: The SAM Team<br>"
            f"Powered by PyQt6, Ollama, Whisper</p>"
            f"</div>"
        )
        about_text.setWordWrap(True)
        about_text.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(about_text)
        return tab

    # ─── Save Logic ───────────────────────────────────────────────

    def _save_settings(self):
        """Tum widget degerlerini config'e yaz ve dosyaya kaydet."""
        try:
            # General
            config.set("hotkey", "trigger", value=self._hotkey_input.text().strip())
            config.set("wake_word", "model", value=self._wake_model_combo.currentText())
            config.set("wake_word", "threshold", value=self._wake_threshold.value())

            # Speech
            config.set("stt", "model", value=self._stt_model_combo.currentText())
            lang_val = self._stt_language.text().strip()
            config.set("stt", "language", value=lang_val if lang_val else None)
            config.set("stt", "device", value=self._stt_device_combo.currentText())
            config.set("tts", "engine", value=self._tts_engine_combo.currentText())
            config.set("tts", "voice", value=self._tts_voice.currentText())
            config.set("tts", "rate", value=self._tts_rate.text().strip())

            # LLM
            config.set("llm", "ollama", "base_url", value=self._ollama_url.text().strip())
            config.set("llm", "ollama", "model", value=self._ollama_model.currentText())
            config.set("llm", "ollama", "temperature", value=self._temp_slider.value() / 100)
            config.set("llm", "ollama", "max_tokens", value=self._max_tokens.value())
            config.set("llm", "context_window", value=self._context_window.value())

            # UI
            config.set("ui", "bar", "width", value=self._bar_width.value())
            config.set("ui", "bar", "height", value=self._bar_height.value())
            config.set("ui", "bar", "opacity", value=self._opacity_slider.value() / 100)
            config.set("ui", "bar", "border_radius", value=self._border_radius.value())
            config.set("ui", "auto_hide", "delay_seconds", value=self._auto_hide.value())

            # Spotify
            config.set("spotify", "client_id", value=self._spotify_client_id.text().strip())
            config.set("spotify", "client_secret", value=self._spotify_client_secret.text().strip())
            config.set("spotify", "redirect_uri", value=self._spotify_redirect.text().strip())

            # Dosyaya kaydet
            success = config.save()

            if success:
                logger.info("Settings saved via UI")
                QMessageBox.information(
                    self, "Settings Saved",
                    "Settings saved successfully.\\nRestart SAM to apply changes."
                )
                self.close()
            else:
                QMessageBox.warning(self, "Error", "Failed to save config file.")

        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            QMessageBox.critical(self, "Error", f"Error saving settings:\n{e}")

    def _browse_custom_wake_model(self):
        """Browse for custom openwakeword model file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Wake Word Model",
            "",
            "Wake Word Models (*.onnx *.tflite);;All Files (*)"
        )
        if file_path:
            import os
            try:
                # Get path relative to the application workspace if possible
                rel_path = os.path.relpath(file_path, os.getcwd())
                if not rel_path.startswith(".."):
                    file_path = rel_path
            except ValueError:
                pass
            
            # Normalize path separators for cross-platform stability
            file_path = file_path.replace("\\", "/")
            
            # Add file path to combo box if not present, and select it
            idx = self._wake_model_combo.findText(file_path)
            if idx < 0:
                self._wake_model_combo.addItem(file_path)
                idx = self._wake_model_combo.count() - 1
            self._wake_model_combo.setCurrentIndex(idx)
