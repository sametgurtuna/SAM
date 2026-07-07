# SAM — Command Router
# Kullanicinin soyledigini analiz eder:
# 1. Sistem komutu mu? → Direkt calistir (LLM gereksiz)
# 2. Soru/sohbet mi? → LLM'e yonlendir
#
# Pattern matching ile calisir — hizli, lokal, bagimliliksiz.

import logging
import re
from typing import Callable, List, Tuple

from commands import system

logger = logging.getLogger(__name__)


class CommandResult:
    """Komut calistirma sonucu."""

    def __init__(self, handled: bool, response: str = "") -> None:
        self.handled = handled   # True = komut bulundu ve calistirildi
        self.response = response # Kullaniciya gosterilecek mesaj


class CommandRouter:
    """
    Transcript'i analiz edip uygun komutu calistirir.
    
    Desteklenen komut kategorileri:
        - Uygulama acma: "open spotify", "launch chrome"
        - Uygulama kapatma: "close spotify", "quit chrome"
        - Ses kontrolu: "volume up", "volume down", "mute"
        - Medya kontrolu: "play", "pause", "next track", "previous track"
        - Sistem: "lock screen", "shutdown", "restart", "screenshot"
        - Web arama: "search for X", "google X"
        - URL acma: "go to youtube.com"
    
    Eslesme bulunamazsa handled=False doner → LLM'e yonlendirilir.
    """

    def __init__(self) -> None:
        # Komut desenleri — (regex_pattern, handler_function)
        # Sirasi onemli: ilk eslesen kazanir
        self._patterns: List[Tuple[re.Pattern, Callable[[re.Match], str]]] = self._build_patterns()

    def try_handle(self, transcript: str) -> CommandResult:
        """
        Transcript'i analiz et. Komutsa calistir, degilse handled=False don.
        
        Args:
            transcript: Whisper'dan gelen metin (kucuk harfe cevrilir)
        
        Returns:
            CommandResult(handled=True/False, response="...")
        """
        text = transcript.lower().strip()

        # Temizlik — gereksiz kelimeleri kaldir
        text = self._clean_text(text)

        logger.debug("Command router input: '%s'", text)

        # Her deseni dene
        for pattern, handler in self._patterns:
            match = pattern.search(text)
            if match:
                try:
                    response = handler(match)
                    logger.info("Command matched: %s → %s", pattern.pattern, response)
                    return CommandResult(handled=True, response=response)
                except Exception as e:
                    logger.error("Command execution failed: %s", e)
                    return CommandResult(handled=True, response="Sorry, that command failed.")

        logger.debug("No command match — forwarding to LLM")
        return CommandResult(handled=False)

    def _clean_text(self, text: str) -> str:
        """Gereksiz bosluk ve noktalama temizle."""
        # Noktalama kaldir
        text = re.sub(r'[.,!?;:\'"]+', '', text)
        # Coklu bosluk temizle
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _build_patterns(self) -> List[Tuple[re.Pattern, Callable[[re.Match], str]]]:
        """Tum komut desenlerini olustur."""
        patterns = []

        # ═══════════════════════════════════════════════════════
        # UYGULAMA ACMA
        # ═══════════════════════════════════════════════════════

        # "open spotify", "open google chrome"
        patterns.append((
            re.compile(r'\b(?:open|launch|start|run)\s+(.+)', re.IGNORECASE),
            lambda m: system.open_app(m.group(1).strip())
        ))

        # ═══════════════════════════════════════════════════════
        # UYGULAMA KAPATMA
        # ═══════════════════════════════════════════════════════

        # "close spotify", "quit chrome"
        patterns.append((
            re.compile(r'\b(?:close|quit|exit|kill)\s+(.+)', re.IGNORECASE),
            lambda m: system.close_app(m.group(1).strip())
        ))

        # ═══════════════════════════════════════════════════════
        # SES KONTROLU
        # ═══════════════════════════════════════════════════════

        # Volume up
        patterns.append((
            re.compile(r'\b(?:volume up|turn up|louder)(?:\s+%?(\d+))?\b', re.IGNORECASE),
            lambda m: system.volume_up(int(m.group(1))) if m.group(1) else system.volume_up()
        ))

        # Volume down
        patterns.append((
            re.compile(r'\b(?:volume down|turn down|quieter)(?:\s+%?(\d+))?\b', re.IGNORECASE),
            lambda m: system.volume_down(int(m.group(1))) if m.group(1) else system.volume_down()
        ))

        # Set absolute volume
        patterns.append((
            re.compile(r'\b(?:set volume|volume to)\s+(?:to\s+)?%?(\d+)%?\b', re.IGNORECASE),
            lambda m: system.set_volume_absolute(int(m.group(1)))
        ))

        # Mute
        patterns.append((
            re.compile(r'\b(?:mute|unmute|toggle mute)\b', re.IGNORECASE),
            lambda m: system.volume_mute()
        ))

        # ═══════════════════════════════════════════════════════
        # MEDYA KONTROLU
        # ═══════════════════════════════════════════════════════

        # Play X on Spotify
        patterns.append((
            re.compile(r'\b(?:play)\s+(.+?)\s+(?:on spotify)\b', re.IGNORECASE),
            lambda m: system.play_on_spotify(m.group(1).strip())
        ))

        # Play/Pause
        patterns.append((
            re.compile(r'\b(?:play|pause|resume)\b', re.IGNORECASE),
            lambda m: system.media_play_pause()
        ))

        # Next track
        patterns.append((
            re.compile(r'\b(?:next|next track|next song|skip)\b', re.IGNORECASE),
            lambda m: system.media_next()
        ))

        # Previous track
        patterns.append((
            re.compile(r'\b(?:previous|prev|previous track|previous song|go back)\b', re.IGNORECASE),
            lambda m: system.media_prev()
        ))

        # ═══════════════════════════════════════════════════════
        # WEB ARAMA
        # ═══════════════════════════════════════════════════════

        # "search for X", "google X"
        patterns.append((
            re.compile(r'\b(?:search|search for|google|look up)\s+(.+)', re.IGNORECASE),
            lambda m: system.web_search(m.group(1).strip())
        ))

        # "go to youtube.com"
        patterns.append((
            re.compile(r'\b(?:go to|open|navigate to)\s+([\w.-]+\.(?:com|org|net|io|dev|co))\b', re.IGNORECASE),
            lambda m: system.open_url(m.group(1).strip())
        ))

        # ═══════════════════════════════════════════════════════
        # SISTEM KOMUTLARI
        # ═══════════════════════════════════════════════════════

        # Lock screen
        patterns.append((
            re.compile(r'\b(?:lock|lock screen|lock computer)\b', re.IGNORECASE),
            lambda m: system.lock_screen()
        ))

        # Screenshot
        patterns.append((
            re.compile(r'\b(?:screenshot|screen shot)\b', re.IGNORECASE),
            lambda m: system.screenshot()
        ))

        # Minimize all
        patterns.append((
            re.compile(r'\b(?:minimize all|show desktop)\b', re.IGNORECASE),
            lambda m: system.minimize_all()
        ))

        # Shutdown
        patterns.append((
            re.compile(r'\b(?:shut ?down|power off)\b', re.IGNORECASE),
            lambda m: system.shutdown_pc()
        ))

        # Restart
        patterns.append((
            re.compile(r'\b(?:restart|reboot)\b', re.IGNORECASE),
            lambda m: system.restart_pc()
        ))

        # Cancel shutdown
        patterns.append((
            re.compile(r'\b(?:cancel shutdown)\b', re.IGNORECASE),
            lambda m: system.cancel_shutdown()
        ))

        return patterns
