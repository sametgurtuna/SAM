# SAM — UI Styles
# All colors, fonts, and QSS stylesheets centralized here.
# No hardcoded colors anywhere else in the UI code.

from core.config import config


class Colors:
    """Color constants pulled from config with fallbacks."""

    @staticmethod
    def background() -> str:
        return config.get("ui", "colors", "background", default="rgba(10, 10, 15, 0.92)")

    @staticmethod
    def accent() -> str:
        return config.get("ui", "colors", "accent", default="#00D4AA")

    @staticmethod
    def accent_listening() -> str:
        return config.get("ui", "colors", "accent_listening", default="#00BFFF")

    @staticmethod
    def accent_thinking() -> str:
        return config.get("ui", "colors", "accent_thinking", default="#FFB84D")

    @staticmethod
    def accent_speaking() -> str:
        return config.get("ui", "colors", "accent_speaking", default="#00D4AA")

    @staticmethod
    def text_primary() -> str:
        return config.get("ui", "colors", "text_primary", default="#E8E8E8")

    @staticmethod
    def text_secondary() -> str:
        return config.get("ui", "colors", "text_secondary", default="#888888")

    @staticmethod
    def border() -> str:
        return config.get("ui", "colors", "border", default="rgba(0, 212, 170, 0.15)")


class Fonts:
    """Font family and size constants."""

    @staticmethod
    def primary() -> str:
        return config.get("ui", "fonts", "primary", default="Segoe UI")

    @staticmethod
    def monospace() -> str:
        return config.get("ui", "fonts", "monospace", default="Cascadia Code")

    @staticmethod
    def fallback() -> str:
        return config.get("ui", "fonts", "fallback", default="Consolas")

    @staticmethod
    def size_transcript() -> int:
        return config.get("ui", "fonts", "size_transcript", default=15)

    @staticmethod
    def size_status() -> int:
        return config.get("ui", "fonts", "size_status", default=11)

    @staticmethod
    def transcript_family() -> str:
        """Full font-family string for transcript text."""
        return f"'{Fonts.primary()}', '{Fonts.monospace()}', '{Fonts.fallback()}', sans-serif"

    @staticmethod
    def status_family() -> str:
        """Full font-family string for status labels."""
        return f"'{Fonts.primary()}', '{Fonts.fallback()}', sans-serif"


def floating_bar_stylesheet() -> str:
    """Main QSS stylesheet for the floating bar container."""
    return f"""
        QFrame#barContainer {{
            background-color: {Colors.background()};
            border: 1px solid {Colors.border()};
            border-radius: {config.get("ui", "bar", "border_radius", default=16)}px;
        }}
    """


def transcript_label_stylesheet() -> str:
    """QSS for the transcript/response text label."""
    return f"""
        QLabel#transcriptLabel {{
            color: {Colors.text_primary()};
            font-family: {Fonts.transcript_family()};
            font-size: {Fonts.size_transcript()}px;
            font-weight: 400;
            background: transparent;
            padding: 0px 8px;
        }}
    """


def status_label_stylesheet() -> str:
    """QSS for the status text label (Listening / Thinking / Speaking)."""
    return f"""
        QLabel#statusLabel {{
            color: {Colors.text_secondary()};
            font-family: {Fonts.status_family()};
            font-size: {Fonts.size_status()}px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
            background: transparent;
            padding: 0px 4px;
        }}
    """
