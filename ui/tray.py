# SAM — System Tray Manager
# Sag altta (system tray) ikon gosterir.
# Sag tik menusu: Settings, Mute, Clear Context, Quit
# Sol tik veya cift tik: Settings penceresini acar.

import logging

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QObject

from ui.icon_generator import create_tray_icon
from ui.settings_window import SettingsWindow

logger = logging.getLogger(__name__)


class TrayManager(QObject):
    """
    System tray ikonu ve menusunu yonetir.
    AppController referansi uzerinden mute/unmute ve context temizleme yapar.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._muted = False
        self._settings_window = None

        # Tray ikonu olustur
        self._tray = QSystemTrayIcon(create_tray_icon(), parent)
        self._tray.setToolTip("SAM — AI Desktop Assistant")

        # Menu olustur
        self._menu = QMenu()
        self._build_menu()
        self._tray.setContextMenu(self._menu)

        # Sol tik → Settings ac
        self._tray.activated.connect(self._on_tray_activated)

        # Goster
        self._tray.show()
        logger.info("System tray icon initialized")

    def _build_menu(self):
        """Sag tik menusu icindeki aksiyonlari olusturur."""
        # Header (Disabled)
        header_action = QAction("✨ SAM Assistant", self._menu)
        header_action.setDisabled(True)
        font = header_action.font()
        font.setBold(True)
        header_action.setFont(font)
        self._menu.addAction(header_action)
        
        self._menu.addSeparator()

        # Settings
        settings_action = QAction("⚙️ Settings...", self._menu)
        settings_action.triggered.connect(self._open_settings)
        self._menu.addAction(settings_action)

        self._menu.addSeparator()

        # Mute / Unmute
        self._mute_action = QAction("🎙️ Mute Wake Word", self._menu)
        self._mute_action.triggered.connect(self._toggle_mute)
        self._menu.addAction(self._mute_action)

        # Clear Context
        clear_action = QAction("🧹 Clear Context", self._menu)
        clear_action.triggered.connect(self._clear_context)
        self._menu.addAction(clear_action)

        self._menu.addSeparator()

        # Quit
        quit_action = QAction("❌ Quit SAM", self._menu)
        quit_action.triggered.connect(self._quit_app)
        self._menu.addAction(quit_action)

    def _on_tray_activated(self, reason):
        """Sol tik veya cift tik → Settings penceresini ac."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._open_settings()

    def _open_settings(self):
        """Settings penceresini ac (tekil instance)."""
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow()
            self._settings_window.show()
        else:
            # Zaten aciksa one getir
            self._settings_window.activateWindow()
            self._settings_window.raise_()

    def _toggle_mute(self):
        """Wake word dinlemeyi ac/kapat."""
        self._muted = not self._muted

        if self._controller is not None:
            if self._muted:
                self._controller._wake_word.pause()
                self._mute_action.setText("🔊 Unmute Wake Word")
                self._tray.showMessage("SAM", "Wake word muted", QSystemTrayIcon.MessageIcon.Information, 2000)
                logger.info("Wake word muted via tray")
            else:
                self._controller._wake_word.resume()
                self._mute_action.setText("🎙️ Mute Wake Word")
                self._tray.showMessage("SAM", "Wake word active", QSystemTrayIcon.MessageIcon.Information, 2000)
                logger.info("Wake word unmuted via tray")

    def _clear_context(self):
        """LLM sohbet gecmisini temizle."""
        if self._controller is not None:
            self._controller._llm.clear_context()
            self._tray.showMessage("SAM", "Conversation context cleared", QSystemTrayIcon.MessageIcon.Information, 2000)
            logger.info("Context cleared via tray")

    def _quit_app(self):
        """Uygulamayi temiz bir sekilde kapat."""
        logger.info("Quit requested from tray menu")
        if self._controller is not None:
            self._controller.shutdown()
        QApplication.quit()

    def cleanup(self):
        """Tray ikonunu temizle."""
        self._tray.hide()
