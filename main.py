# SAM — AI Desktop Assistant
# Entry point. Initializes the application, loads config, and starts the UI.

import sys
import os
import logging

# Ensure project root is on Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from core.config import config
from core.app import AppController
from ui.tray import TrayManager


def setup_logging() -> None:
    """Configure logging to file and console."""
    log_file = config.get("logging", "file", default="logs/sam.log")
    log_level = config.get("logging", "level", default="DEBUG")

    # Create logs directory
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(os.path.join(project_root, log_dir), exist_ok=True)

    log_path = os.path.join(project_root, log_file)

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.DEBUG),
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    """SAM entry point."""
    # Load config first
    config.load()

    # Setup logging
    setup_logging()

    logger = logging.getLogger("sam.main")
    logger.info("=" * 50)
    logger.info("SAM v%s starting up", config.get("app", "version", default="0.1.0"))
    logger.info("=" * 50)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName(config.get("app", "name", default="SAM"))
    app.setQuitOnLastWindowClosed(False)  # SAM runs as a background app

    # High DPI support
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Initialize the controller (registers hotkey, creates floating bar)
    controller = AppController()

    # Initialize system tray icon & menu
    tray = TrayManager(controller=controller)

    hotkey = config.get("hotkey", "trigger", default="ctrl+space")
    wake_word = config.get("wake_word", "model", default="hey_jarvis")
    # Format wake word name for display
    wake_display = os.path.basename(wake_word).replace(".onnx", "").replace(".tflite", "").replace("_", " ").title()
    wake_msg = f"Say '{wake_display}' to activate (voice)"

    llm_engine = controller._llm.active_engine_name
    logger.info("SAM is ready. LLM: %s", llm_engine)
    print(f"\n  +--------------------------------------------+")
    print(f"  |   SAM - AI Desktop Assistant  v0.3.0       |")
    print(f"  |                                            |")
    print(f"  |   {wake_msg:<40s} |")
    print(f"  |   Press {hotkey.upper():<12s} to activate (key)     |")
    print(f"  |   Press ESC           to dismiss            |")
    print(f"  |   Press CTRL+C        to quit               |")
    print(f"  |                                            |")
    print(f"  |   LLM: {llm_engine:<35s}|")
    print(f"  |   Tray icon active (right-click for menu)  |")
    print(f"  +--------------------------------------------+\n")

    # Run event loop
    try:
        exit_code = app.exec()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        exit_code = 0
    finally:
        tray.cleanup()
        controller.shutdown()

    logger.info("SAM shutdown. Exit code: %d", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
