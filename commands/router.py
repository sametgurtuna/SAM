# SAM — Command Router
# Analyzes user input:
# 1. System command? → Execute directly (bypasses LLM)
# 2. Conversational query? → Route to LLM
#
# Pattern-matching based — fast, local, zero-dependency.

import logging
import re
from typing import Callable, List, Tuple

from commands import system

logger = logging.getLogger(__name__)


class CommandResult:
    """Result of command execution."""

    def __init__(self, handled: bool, response: str = "", image_b64: str | None = None) -> None:
        self.handled = handled       # True = command was matched and executed
        self.response = response     # Response message for the user
        self.image_b64 = image_b64   # Screenshot for vision LLM


class CommandRouter:
    """
    Analyzes transcripts and executes matching system commands.
    
    Supported command categories:
        - App launch: "open spotify", "launch chrome"
        - App terminate: "close spotify", "quit chrome"
        - Volume control: "volume up", "volume down", "mute"
        - Media playback: "play", "pause", "next track", "previous track"
        - System control: "lock screen", "shutdown", "restart", "screenshot"
        - Web search: "search for X", "google X"
        - URL navigation: "go to youtube.com"
    
    Returns handled=False when no command pattern matches → routed to LLM.
    """

    def __init__(self) -> None:
        # Command patterns — (regex_pattern, handler_function)
        # Order matters: first match wins
        self._patterns: List[Tuple[re.Pattern, Callable[[re.Match], str]]] = self._build_patterns()
        self._vision_patterns: List[re.Pattern] = self._build_vision_patterns()

    def try_handle(self, transcript: str, *, vision: bool = True) -> CommandResult:
        """
        Analyze transcript. If command matches, execute and return handled=True.
        Supports chained multi-commands ("and", "ve", "then").
        """
        text = transcript.lower().strip()
        text = self._clean_text(text)

        logger.debug("Command router input: '%s'", text)

        # Vision pattern check — capture screen if user requested visual analysis
        for v_pat in (self._vision_patterns if vision else ()):
            if v_pat.search(text):
                from commands.vision import capture_screen_base64
                logger.info("Vision intent matched: %s", text)
                b64 = capture_screen_base64()
                # Handled=False because LLM still generates the textual answer with image attached
                return CommandResult(handled=False, image_b64=b64)

        # Split chained commands (" and ", " ve ", " then ")
        split_pattern = re.compile(r'\s+\band\b\s+|\s+\bve\b\s+|\s+\bthen\b\s+')
        parts = split_pattern.split(text)

        if len(parts) > 1:
            # If all sub-phrases are commands, execute sequentially
            matches = []
            for part in parts:
                part = part.strip()
                if not part:
                    continue
                match_info = self._get_match(part)
                if not match_info:
                    matches = None
                    break
                matches.append(match_info)
            
            if matches:
                import time
                responses = []
                for i, (handler, match) in enumerate(matches):
                    try:
                        resp = handler(match)
                        if resp:
                            responses.append(resp)
                            
                        # Brief pause between chained commands
                        if i < len(matches) - 1:
                            if resp and ("Opening" in resp or "Trying to open" in resp):
                                time.sleep(3.0)
                            else:
                                time.sleep(0.5)
                    except Exception as e:
                        logger.error("Command in chain failed: %s", e)
                
                return CommandResult(handled=True, response=" and ".join(responses))

        # Single command matching
        match_info = self._get_match(text)
        if match_info:
            handler, match = match_info
            try:
                response = handler(match)
                logger.info("Command matched: %s → %s", text, response)
                return CommandResult(handled=True, response=response)
            except Exception as e:
                logger.error("Command execution failed: %s", e)
                return CommandResult(handled=True, response="Sorry, that command failed.")

        logger.debug("No command match — forwarding to LLM")
        return CommandResult(handled=False)

    def _get_match(self, text: str):
        """Find matching command pattern for given text."""
        for pattern, handler in self._patterns:
            match = pattern.search(text)
            if match:
                return (handler, match)
        return None

    def _clean_text(self, text: str) -> str:
        """Strip filler words, address tokens, and excess punctuation."""
        # Remove punctuation
        text = re.sub(r'[.,!?;:\'"]+', '', text)
        # Remove address tokens and polite prefixes
        text = re.sub(r'^(?:hey\s+sam|sam|please|lütfen|lutfen|can\s+you|bana)\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+(?:please|lütfen|lutfen)$', '', text, flags=re.IGNORECASE)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _build_patterns(self) -> List[Tuple[re.Pattern, Callable[[re.Match], str]]]:
        """Build list of command pattern tuples."""
        patterns = []

        # ═══════════════════════════════════════════════════════
        # MEDIA PLAYBACK (EN + TR)
        # ═══════════════════════════════════════════════════════

        # Play X on Spotify
        patterns.append((
            re.compile(r'\b(?:play)\s+(.+?)\s+(?:on spotify)\b', re.IGNORECASE),
            lambda m: system.play_on_spotify(m.group(1).strip())
        ))

        # Next track
        patterns.append((
            re.compile(
                r'^(?:(?:play|go\s+to|skip\s+to|oynat|geç|gec)\s+)?'
                r'(?:next|next\s+track|next\s+song|skip|skip\s+song|'
                r'sonraki|sonraki\s+parça|sonraki\s+parca|sonraki\s+şarkı|sonraki\s+sarki|'
                r'sıradaki|siradaki|sıradaki\s+parça|sıradaki\s+şarkı|şarkıyı\s+geç|sarkiyi\s+gec|'
                r'geç|gec|pas\s+geç|pas\s+gec|bir\s+sonraki)'
                r'(?:\s+(?:parçaya|parcaya|şarkıya|sarkiya|track|song|please|lütfen|lutfen))?'
                r'(?:\s+(?:geç|gec))?$',
                re.IGNORECASE
            ),
            lambda m: system.media_next()
        ))

        # Previous track
        patterns.append((
            re.compile(
                r'^(?:(?:play|go\s+to|oynat)\s+)?'
                r'(?:previous|prev|previous\s+track|previous\s+song|go\s+back|'
                r'önceki|onceki|önceki\s+parça|onceki\s+parca|önceki\s+şarkı|onceki\s+sarki|'
                r'bir\s+önceki|öncekine\s+geç|oncekine\s+gec)'
                r'(?:\s+(?:parçaya|parcaya|şarkıya|sarkiya|track|song))?'
                r'(?:\s+(?:geç|gec))?$',
                re.IGNORECASE
            ),
            lambda m: system.media_prev()
        ))

        # Play/Pause
        patterns.append((
            re.compile(
                r'^(?:play|pause|resume|stop|oynat|durdur|duraklat|devam\s+et|müziği\s+durdur|muzigi\s+durdur|müziği\s+başlat|muzigi\s+baslat)$',
                re.IGNORECASE
            ),
            lambda m: system.media_play_pause()
        ))

        # ═══════════════════════════════════════════════════════
        # VOLUME CONTROL (EN + TR)
        # ═══════════════════════════════════════════════════════

        # Volume up
        patterns.append((
            re.compile(
                r'\b(?:volume\s+up|turn\s+up|louder|increase\s+volume|sesi\s+aç|sesi\s+ac|sesi\s+yükselt|sesi\s+yukselt|sesi\s+artır|sesi\s+arttir)(?:\s+%?(\d+))?\b',
                re.IGNORECASE
            ),
            lambda m: system.volume_up(int(m.group(1))) if m.group(1) else system.volume_up()
        ))

        # Volume down
        patterns.append((
            re.compile(
                r'\b(?:volume\s+down|turn\s+down|quieter|decrease\s+volume|sesi\s+kıs|sesi\s+kis|sesi\s+azalt|sesi\s+düşür|sesi\s+dusur)(?:\s+%?(\d+))?\b',
                re.IGNORECASE
            ),
            lambda m: system.volume_down(int(m.group(1))) if m.group(1) else system.volume_down()
        ))

        # Set absolute volume
        patterns.append((
            re.compile(r'\b(?:set\s+volume|volume\s+to|sesi\s+seviyesini)\s+(?:to\s+)?%?(\d+)%?\b', re.IGNORECASE),
            lambda m: system.set_volume_absolute(int(m.group(1)))
        ))

        # Mute / Unmute
        patterns.append((
            re.compile(r'\b(?:mute|unmute|toggle\s+mute|sesi\s+kapat|sessiz|sessize\s+al)\b', re.IGNORECASE),
            lambda m: system.volume_mute()
        ))

        # ═══════════════════════════════════════════════════════
        # SYSTEM COMMANDS (EN + TR)
        # ═══════════════════════════════════════════════════════

        # Lock screen
        patterns.append((
            re.compile(
                r'^(?:lock(?:\s+(?:the\s+)?(?:screen|computer|pc|workstation))?|ekranı\s+kilitle|ekrani\s+kilitle|kilitle)$',
                re.IGNORECASE
            ),
            lambda m: system.lock_screen()
        ))

        # Screenshot
        patterns.append((
            re.compile(
                r'^(?:take\s+a\s+|take\s+)?(?:screenshot|screen\s+shot)|ekran\s+görüntüsü\s+al|ekran\s+goruntusu\s+al|ekran\s+görüntüsü|ekran\s+goruntusu$',
                re.IGNORECASE
            ),
            lambda m: system.screenshot()
        ))

        # Minimize all
        patterns.append((
            re.compile(r'\b(?:minimize\s+all|show\s+desktop|masaüstünü\s+göster|masaustunu\s+goster)\b', re.IGNORECASE),
            lambda m: system.minimize_all()
        ))

        # Cancel shutdown
        patterns.append((
            re.compile(r'\b(?:cancel|abort|stop|iptal\s+et)\s+(?:the\s+)?(?:shutdown|shut\s+down|restart|reboot|kapatma)\b', re.IGNORECASE),
            lambda m: system.cancel_shutdown()
        ))

        # Power confirmation
        patterns.append((
            re.compile(r'^(?:confirm|yes\s+confirm|confirm\s+it|do\s+it|onayla|evet\s+onayla)$', re.IGNORECASE),
            lambda m: system.confirm_power_action()
        ))

        # Shutdown
        patterns.append((
            re.compile(
                r'^(?:shut\s*down|power\s+off|turn\s+off)\s+(?:the\s+|my\s+)?(?:computer|pc|machine|system|laptop)$|^(?:bilgisayarı\s+kapat|sistemi\s+kapat)$',
                re.IGNORECASE
            ),
            lambda m: system.shutdown_pc()
        ))

        # Restart
        patterns.append((
            re.compile(
                r'^(?:restart|reboot)\s+(?:the\s+|my\s+)?(?:computer|pc|machine|system|laptop)$|^(?:bilgisayarı\s+yeniden\s+başlat|yeniden\s+başlat)$',
                re.IGNORECASE
            ),
            lambda m: system.restart_pc()
        ))

        # ═══════════════════════════════════════════════════════
        # APP LAUNCH / CLOSE (EN + TR)
        # ═══════════════════════════════════════════════════════

        # "open spotify", "launch chrome", "aç spotify"
        patterns.append((
            re.compile(r'^(?:open|launch|start|run|aç|ac|başlat|baslat)\s+(.+)', re.IGNORECASE),
            lambda m: system.open_app(m.group(1).strip())
        ))
        # "chrome aç", "spotify aç"
        patterns.append((
            re.compile(r'^(?!sesi|müziği|muzigi|ekranı|ekrani)(.+?)\s+(?:aç|ac|başlat|baslat)$', re.IGNORECASE),
            lambda m: system.open_app(m.group(1).strip())
        ))

        # "close spotify", "quit chrome", "kapat spotify"
        patterns.append((
            re.compile(r'^(?:close|quit|exit|kill|kapat|durdur)\s+(.+)', re.IGNORECASE),
            lambda m: system.close_app(m.group(1).strip())
        ))
        # "chrome kapat", "spotify kapat"
        patterns.append((
            re.compile(r'^(?!sesi|müziği|muzigi|ekranı|ekrani)(.+?)\s+(?:kapat|durdur)$', re.IGNORECASE),
            lambda m: system.close_app(m.group(1).strip())
        ))

        # ═══════════════════════════════════════════════════════
        # WEB SEARCH & URL
        # ═══════════════════════════════════════════════════════

        # "search for X", "google X", "X ara"
        patterns.append((
            re.compile(r'\b(?:search|search\s+for|google|look\s+up|ara)\s+(.+)', re.IGNORECASE),
            lambda m: system.web_search(m.group(1).strip())
        ))

        # "go to youtube.com"
        patterns.append((
            re.compile(r'\b(?:go\s+to|open|navigate\s+to)\s+([\w.-]+\.(?:com|org|net|io|dev|co))\b', re.IGNORECASE),
            lambda m: system.open_url(m.group(1).strip())
        ))

        return patterns

    def _build_vision_patterns(self) -> List[re.Pattern]:
        """Patterns to detect screen analysis intent."""
        return [
            re.compile(r'\b(?:analyze|look at|read|describe)\s+(?:my\s+)?(?:screen|desktop|display)\b', re.IGNORECASE),
            re.compile(r'\bwhat(?:\'s| is)\s+on\s+my\s+screen\b', re.IGNORECASE),
            re.compile(r'\bekran(?:imi|i)?\s+(?:analiz|incele|oku)\b', re.IGNORECASE),
            re.compile(r'\bekran(?:im)?da\s+ne\s+var\b', re.IGNORECASE),
        ]
