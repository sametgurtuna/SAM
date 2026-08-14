import os
import logging

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QObject

from ui.icon_generator import create_tray_icon
from ui.web_settings import launch_web_settings

logger = logging.getLogger(__name__)


class TrayManager(QObject):
    """
    Manages system tray icon and context menu.
    Provides mute/unmute, context clearing, and settings access via AppController.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._muted = False
        self._settings_window = None

        # Create tray icon — use assets/icon.ico if present, otherwise render
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.ico"))
        if not os.path.exists(icon_path):
            icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "icon.png"))

        if os.path.exists(icon_path):
            tray_icon = QIcon(icon_path)
        else:
            tray_icon = create_tray_icon()

        self._tray = QSystemTrayIcon(tray_icon, parent)
        self._tray.setToolTip("SAM — AI Desktop Assistant")

        # Build context menu
        self._menu = QMenu()
        self._build_menu()
        self._tray.setContextMenu(self._menu)

        # Left click → Open settings
        self._tray.activated.connect(self._on_tray_activated)

        # Show
        self._tray.show()
        logger.info("System tray icon initialized")

    def _build_menu(self):
        """Construct actions for the tray context menu."""
        # Header (Disabled)
        header_action = QAction("✨ SAM Assistant", self._menu)
        header_action.setDisabled(True)
        font = header_action.font()
        font.setBold(True)
        header_action.setFont(font)
        self._menu.addAction(header_action)
        
        self._menu.addSeparator()

        # Ask SAM (typed input)
        ask_action = QAction("⌨️ Ask SAM...", self._menu)
        ask_action.triggered.connect(self._open_text_input)
        self._menu.addAction(ask_action)

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
        """Left click → open Settings window."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._open_settings()

    def _open_settings(self):
        """Open Settings window (debounced singleton instance)."""
        import time
        now = time.time()
        if hasattr(self, "_last_settings_click") and now - self._last_settings_click < 1.2:
            return
        self._last_settings_click = now
        launch_web_settings(controller=self._controller)

    def _open_text_input(self):
        """Open typed text input below the orb."""
        if self._controller is not None:
            self._controller.text_input_signal.emit()

    def _toggle_mute(self):
        """Toggle wake word listening on/off."""
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
        """Clear conversation history."""
        if self._controller is not None:
            self._controller._llm.clear_context()
            self._tray.showMessage("SAM", "Conversation context cleared", QSystemTrayIcon.MessageIcon.Information, 2000)
            logger.info("Context cleared via tray")

    def _quit_app(self):
        """Gracefully shut down application."""
        logger.info("Quit requested from tray menu")
        if self._controller is not None:
            self._controller.shutdown()
        QApplication.quit()

    def cleanup(self):
        """Clean up system tray icon."""
        self._tray.hide()
