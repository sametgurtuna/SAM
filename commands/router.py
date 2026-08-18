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

    def __init__(
        self,
        handled: bool,
        response: str = "",
        image_b64: str | None = None,
        clipboard_text: str | None = None,
        toast: tuple[str, str] | None = None,
        language_action: str | None = None,
    ) -> None:
        self.handled = handled             # True = command was matched and executed
        self.response = response           # Response message for the user
        self.image_b64 = image_b64         # Screenshot for vision LLM
        self.clipboard_text = clipboard_text  # Text from clipboard for LLM context
        self.toast = toast                 # Ephemeral HUD badge (icon, message)
        self.language_action = language_action  # "tr", "en", "auto", or None


class CommandRouter:
    """
    Analyzes transcripts and executes matching system commands.
    
    Supported command categories:
        - App launch: "open spotify", "launch chrome"
        - App terminate: "close spotify", "quit chrome"
        - Volume control: "volume up", "volume down", "mute"
        - Media playback: "play", "pause", "next track", "previous track"
        - System control: "lock screen", "shutdown", "restart", "screenshot"
        - Language control: "türkçe konuş", "switch to english", "auto language"
        - Web search: "search for X", "google X"
        - URL navigation: "go to youtube.com"
    
    Returns handled=False when no command pattern matches → routed to LLM.
    """

    def __init__(self) -> None:
        # Command patterns — (regex_pattern, handler_function)
        # Order matters: first match wins
        self._patterns: List[Tuple[re.Pattern, Callable[[re.Match], str]]] = self._build_patterns()
        self._vision_patterns: List[re.Pattern] = self._build_vision_patterns()
        self._clipboard_patterns: List[re.Pattern] = self._build_clipboard_patterns()

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

        # Clipboard pattern check — fetch clipboard text if user requested clipboard action
        for c_pat in self._clipboard_patterns:
            if c_pat.search(text):
                from commands.clipboard import get_clipboard_text
                logger.info("Clipboard intent matched: %s", text)
                clip_text = get_clipboard_text()
                if clip_text:
                    return CommandResult(handled=False, clipboard_text=clip_text)
                else:
                    is_tr = any(w in text for w in ("bunu", "bu", "pano", "koddaki", "özetle", "çevir", "açıkla", "düzelt"))
                    msg = (
                        "Panoda kopyalanmış herhangi bir metin bulunamadı."
                        if is_tr
                        else "No text found in your clipboard. Please copy some text first."
                    )
                    return CommandResult(handled=True, response=msg, toast=("⚠️", "Clipboard Empty"))

        # Language switching commands
        if text in ("türkçe konuş", "türkçeye geç", "turkceye gec", "türkçe mod", "türkçe", "turkce"):
            return CommandResult(
                handled=True,
                response="Türkçe diline geçildi.",
                language_action="tr",
                toast=("🌐", "Language: Turkish (TR)"),
            )
        if text in ("switch to english", "speak english", "english mode", "english"):
            return CommandResult(
                handled=True,
                response="Switched to English.",
                language_action="en",
                toast=("🌐", "Language: English (EN)"),
            )
        if text in ("otomatik dil", "otomatik dile geç", "auto language", "auto detect language", "auto detect"):
            return CommandResult(
                handled=True,
                response="Automatic language detection enabled.",
                language_action="auto",
                toast=("🌐", "Language: Auto Detect"),
            )

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
                
                resp_text = " and ".join(responses)
                return CommandResult(handled=True, response=resp_text, toast=self._infer_toast(resp_text, text))

        # Single command matching
        match_info = self._get_match(text)
        if match_info:
            handler, match = match_info
            try:
                response = handler(match)
                logger.info("Command matched: %s → %s", text, response)
                return CommandResult(handled=True, response=response, toast=self._infer_toast(response, text))
            except Exception as e:
                logger.error("Command execution failed: %s", e)
                return CommandResult(handled=True, response="Sorry, that command failed.", toast=("⚠️", "Command Failed"))

        logger.debug("No command match — forwarding to LLM")
        return CommandResult(handled=False)

    def _infer_toast(self, response: str, text: str) -> tuple[str, str]:
        """Generate an intuitive icon and short HUD toast message from command execution."""
        t_low = text.lower()
        r_low = response.lower()

        if any(w in t_low for w in ("volume", "sesi", "turn up", "turn down", "louder", "quieter")):
            return ("🔊", response)
        if any(w in t_low for w in ("mute", "unmute", "sessiz", "sessize")):
            return ("🔇" if "mute" in r_low or "sessiz" in r_low else "🔊", response)
        if any(w in t_low for w in ("next", "sonraki", "sıradaki", "skip")):
            return ("🎵", "Next Track")
        if any(w in t_low for w in ("previous", "prev", "önceki")):
            return ("🎵", "Previous Track")
        if any(w in t_low for w in ("play", "pause", "resume", "oynat", "durdur", "duraklat")):
            return ("⏯️", response or "Media Toggled")
        if any(w in t_low for w in ("lock", "kilitle")):
            return ("🔒", "Screen Locked")
        if any(w in t_low for w in ("screenshot", "ekran görüntüsü")):
            return ("📸", "Screenshot Saved")
        if "opening" in r_low or "açılıyor" in r_low:
            return ("🚀", response)
        if "closing" in r_low or "kapatılıyor" in r_low:
            return ("⏹️", response)

        return ("⚡", response[:32])

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

    def _build_clipboard_patterns(self) -> List[re.Pattern]:
        """Patterns to detect clipboard-aware queries (TR + EN)."""
        return [
            # Turkish triggers
            re.compile(r'^(?:bunu|bunu\s+bana)\s+(?:açıkla|acikla|anlat|çözümle|cozumle)(?:\s+(?:lütfen|lutfen|misin|mısın))?$', re.IGNORECASE),
            re.compile(r'^(?:bunu|bu\s+metni|kopyaladığım\s+metni|kopyaladigim\s+metni)\s+(?:çevir|cevir|türkçeye\s+çevir|turkceye\s+cevir|ingilizceye\s+çevir|ingilizceye\s+cevir)(?:\s+(?:lütfen|lutfen))?$', re.IGNORECASE),
            re.compile(r'^(?:bu\s+koddaki\s+hatayı\s+bul|bu\s+koddaki\s+hatayi\s+bul|bu\s+koddaki\s+hata\s+ne|bu\s+kodu\s+düzelt|bu\s+kodu\s+duzelt|koddaki\s+hatayı\s+bul|koddaki\s+hatayi\s+bul|kodu\s+incele)$', re.IGNORECASE),
            re.compile(r'^(?:bunu\s+özetle|bunu\s+ozetle|özetle|ozetle|metni\s+özetle|metni\s+ozetle)$', re.IGNORECASE),
            re.compile(r'^(?:panodakini\s+oku|panodakini\s+açıkla|panodakini\s+acikla|panoda\s+ne\s+var|panodaki\s+metni\s+açıkla|panodaki\s+metni\s+acikla|panoyu\s+oku)$', re.IGNORECASE),
            re.compile(r'^(?:bu\s+ne\s+demek|bu\s+ne\s+anlama\s+geliyor)$', re.IGNORECASE),

            # English triggers
            re.compile(r'^(?:explain|describe|clarify)\s+(?:this|that)(?:\s+(?:to\s+me|please))?$', re.IGNORECASE),
            re.compile(r'^(?:translate\s+(?:this|that)(?:\s+(?:to\s+turkish|to\s+english))?)$', re.IGNORECASE),
            re.compile(r'^(?:find\s+(?:the\s+)?(?:bug|error)\s+in\s+this(?:\s+code)?|fix\s+this(?:\s+code)?|debug\s+this(?:\s+code)?|what(?:\'s|\s+is)\s+wrong\s+with\s+this(?:\s+code)?)$', re.IGNORECASE),
            re.compile(r'^(?:summarize\s+(?:this|that)|give\s+me\s+a\s+summary|summarize\s+this\s+text)$', re.IGNORECASE),
            re.compile(r'^(?:what(?:\'s|\s+is)\s+on\s+my\s+clipboard|read\s+(?:my\s+)?clipboard|explain\s+clipboard)$', re.IGNORECASE),
        ]
