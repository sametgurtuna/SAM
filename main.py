# SAM — AI Desktop Assistant
# Entry point. Initializes the application, loads config, and starts the UI.

import sys
import os
import logging

# Ensure project root is on Python path (frozen builds already have it)
project_root = os.path.dirname(os.path.abspath(__file__))
if not getattr(sys, "frozen", False) and project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from core import paths
from core.config import config
from core.app import AppController
from ui.tray import TrayManager


def setup_logging() -> None:
    """Configure logging to file and (when there is one) console."""
    log_file = config.get("logging", "file", default="logs/sam.log")
    log_level = config.get("logging", "level", default="DEBUG")

    log_path = os.path.join(paths.logs_dir(), os.path.basename(log_file))

    # --noconsole builds have sys.stdout == None; StreamHandler would raise.
    handlers: list[logging.Handler] = [
        logging.FileHandler(log_path, encoding="utf-8")
    ]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.DEBUG),
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
    )

    # Ucuncu parti kutuphaneler DEBUG'ta her HTTP basligini yaziyor —
    # log dosyasini kullanilmaz hale getiriyor ve her satir icin disk I/O
    # maliyeti cikariyor. Bunlari WARNING'e sabitle.
    for noisy in (
        "urllib3", "httpcore", "httpx", "requests",
        "huggingface_hub", "filelock", "asyncio",
        "comtypes", "PIL", "matplotlib",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main() -> None:
    """SAM entry point."""
    # Installer helper mode — download models and exit, no Qt, no UI.
    # Must run before QApplication is constructed.
    if "--install-models" in sys.argv:
        from core.installer_steps import run_install_steps
        sys.exit(run_install_steps(sys.argv))

    # Tek ornek kilidi — Windows acilisina eklendiginde elle bir kez daha
    # baslatmak iki orb ve iki mikrofon akisi yaratirdi.
    if not paths.single_instance_lock():
        if sys.stdout is not None:
            print("SAM is already running (check the system tray).")
        sys.exit(0)

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
    text_hotkey = config.get("hotkey", "text_input", default="ctrl+shift+space")
    wake_word = config.get("wake_word", "model", default="hey_jarvis")
    # Format wake word name for display
    wake_display = os.path.basename(wake_word).replace(".onnx", "").replace(".tflite", "").replace("_", " ").title()
    wake_msg = f"Say '{wake_display}' to activate (voice)"

    llm_engine = controller._llm.active_engine_name
    version = config.get("app", "version", default="0.1.0")
    logger.info("SAM is ready. LLM: %s", llm_engine)

    # --noconsole builds have no stdout — print() would raise there.
    if sys.stdout is not None:
        print(f"\n  +--------------------------------------------+")
        print(f"  |   SAM - AI Desktop Assistant  v{version:<12s}|")
        print(f"  |                                            |")
        print(f"  |   {wake_msg:<40s} |")
        print(f"  |   Press {hotkey.upper():<12s} to speak            |")
        print(f"  |   Press {text_hotkey.upper():<12s} to type             |")
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
