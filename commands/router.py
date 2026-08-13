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

    def __init__(self, handled: bool, response: str = "", image_b64: str | None = None) -> None:
        self.handled = handled   # True = komut bulundu ve calistirildi
        self.response = response # Kullaniciya gosterilecek mesaj
        self.image_b64 = image_b64 # Vision LLM icin ekran goruntusu


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
        self._vision_patterns: List[re.Pattern] = self._build_vision_patterns()

    def try_handle(self, transcript: str) -> CommandResult:
        """
        Transcript'i analiz et. Komutsa calistir, degilse handled=False don.
        Zincirleme komutlari (and/ve) destekler.
        """
        text = transcript.lower().strip()
        text = self._clean_text(text)

        logger.debug("Command router input: '%s'", text)

        # Vision pattern kontrolu - eger eslesirse ekrani yakala ve LLM'e gonder
        for v_pat in self._vision_patterns:
            if v_pat.search(text):
                from commands.vision import capture_screen_base64
                logger.info("Vision intent matched: %s", text)
                b64 = capture_screen_base64()
                # Handled=False cunku LLM hala metni islemeli, ancak resim eklendi
                return CommandResult(handled=False, image_b64=b64)

        # " and ", " ve ", " then " ile ayir
        split_pattern = re.compile(r'\s+\band\b\s+|\s+\bve\b\s+|\s+\bthen\b\s+')
        parts = split_pattern.split(text)

        if len(parts) > 1:
            # Eger birden fazla parca varsa ve HEPSI komutsa zincirleme calistir.
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
                # Hepsi komutmus! Sirayla calistir.
                responses = []
                for i, (handler, match) in enumerate(matches):
                    try:
                        resp = handler(match)
                        if resp:
                            responses.append(resp)
                            
                        # Zincirdeki komutlar arasinda bekle
                        if i < len(matches) - 1:
                            # Eger bir uygulama aciyorsak, yuklenmesi icin ekstra sure tani
                            if resp and ("Opening" in resp or "Trying to open" in resp):
                                time.sleep(3.0)
                            else:
                                time.sleep(0.5)
                    except Exception as e:
                        logger.error("Command in chain failed: %s", e)
                
                return CommandResult(handled=True, response=" and ".join(responses))

        # Zincir degilse veya parcalardan biri komut degilse, tek parca olarak dene
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
        """Metin icin uygun komut desenini bulur."""
        for pattern, handler in self._patterns:
            match = pattern.search(text)
            if match:
                return (handler, match)
        return None

    def _clean_text(self, text: str) -> str:
        """Gereksiz bosluk, noktalama ve dolgu kelimeleri temizle."""
        # Noktalama kaldir
        text = re.sub(r'[.,!?;:\'"]+', '', text)
        # Dolgu / nezaket kelimelerini ve samet/sam ses hitaplarini temizle
        text = re.sub(r'^(?:hey\s+sam|sam|please|lütfen|lutfen|can\s+you|bana)\s+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+(?:please|lütfen|lutfen)$', '', text, flags=re.IGNORECASE)
        # Coklu bosluk temizle
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _build_patterns(self) -> List[Tuple[re.Pattern, Callable[[re.Match], str]]]:
        """Tum komut desenlerini olustur."""
        patterns = []

        # ═══════════════════════════════════════════════════════
        # MEDYA KONTROLU (EN + TR)
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
        # SES KONTROLU (EN + TR)
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
        # SISTEM KOMUTLARI (EN + TR)
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

        # Guc islemi onayi
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
        # UYGULAMA ACMA / KAPATMA (EN + TR)
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
        # WEB ARAMA & URL
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
        """Ekran analizi niyetlerini tespit etmek icin desenler."""
        return [
            re.compile(r'\b(?:analyze|look at|read|describe)\s+(?:my\s+)?(?:screen|desktop|display)\b', re.IGNORECASE),
            re.compile(r'\bwhat(?:\'s| is)\s+on\s+my\s+screen\b', re.IGNORECASE),
            re.compile(r'\bekran(?:imi|i)?\s+(?:analiz|incele|oku)\b', re.IGNORECASE),
            re.compile(r'\bekran(?:im)?da\s+ne\s+var\b', re.IGNORECASE),
        ]
