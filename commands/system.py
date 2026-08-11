# SAM — System Commands
# Bilgisayar uzerinde direkt islem yapan komutlar:
# uygulama acma/kapatma, ses kontrolu, ekran kilitleme, vb.

import ctypes
import logging
import os
import re
import subprocess
import time
import urllib.parse
from typing import Optional, Dict, Any

from core import paths

# Spotipy is lazy-loaded in the function to prevent slow startup,
# but we can import it at the top if it's available. 
# We'll keep it lazy-loaded inside `play_on_spotify` to ensure 
# the assistant boots fast even if spotipy isn't configured, 
# but we'll move `os` and `urllib` to the top.

logger = logging.getLogger(__name__)

# ─── Windows API Sabitleri ────────────────────────────────────

# Ses kontrolu icin virtual key codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT = 0xB0
VK_MEDIA_PREV = 0xB1

KEYEVENTF_KEYUP = 0x0002


# ─── Guvenlik ─────────────────────────────────────────────────
# Transcript metni STT'den gelir ve dogrudan isletim sistemine
# aktarilir. Kabuk metakarakterleri iceren hicbir isim kabul
# edilmez — sadece harf, rakam, bosluk ve birkac guvenli isaret.
_SAFE_APP_NAME_RE = re.compile(r"^[\w .'-]{1,64}$", re.UNICODE)


def _is_safe_name(name: str) -> bool:
    """Uygulama adinin isletim sistemine gecirilmesi guvenli mi?"""
    return bool(_SAFE_APP_NAME_RE.match(name.strip()))


def _user_cache_dir() -> str:
    """SAM'in kullaniciya ozel cache dizini (token'lar burada tutulur)."""
    return paths.cache_dir()


# ─── Bilinen Uygulamalar ──────────────────────────────────────
# Anahtar: kucultumus isim → (arama_deseni, baslatma_komutu)
# Oncelik: shell start (Windows baslat menusunden bulur) > direkt yol

# Sesle veya yazi ile ASLA acilmayacak uygulamalar — hepsi bir kabuk/komut
# istemi. Whisper hallusinasyonlari veya STT hatalari bunlari tetikleyebilir;
# beklenmedik bir terminal acilmasi kullaniciyi korkutur (bkz. open_app()).
_BLOCKED_APP_NAMES = frozenset({
    "cmd", "command prompt", "terminal", "windows terminal",
    "powershell", "power shell", "pwsh", "wt", "bash", "wsl",
    "windows subsystem for linux", "git bash", "conemu",
})

KNOWN_APPS: Dict[str, Dict[str, Any]] = {
    # Tarayicilar
    "chrome": {
        "exe": "chrome.exe",
        "start": "chrome",
        "aliases": ["chrome", "google chrome"],
    },
    "firefox": {
        "exe": "firefox.exe",
        "start": "firefox",
        "aliases": ["firefox", "fire fox"],
    },
    "edge": {
        "exe": "msedge.exe",
        "start": "msedge",
        "aliases": ["edge", "microsoft edge"],
    },
    "brave": {
        "exe": "brave.exe",
        "start": "brave",
        "aliases": ["brave"],
    },
    # Muzik / Video
    "spotify": {
        "exe": "Spotify.exe",
        "start": "spotify",
        "protocol": "spotify:",
        "aliases": ["spotify"],
    },
    "vlc": {
        "exe": "vlc.exe",
        "start": "vlc",
        "aliases": ["vlc", "media player"],
    },
    # Mesajlasma
    "discord": {
        "exe": "Discord.exe",
        "start": "discord",
        "aliases": ["discord"],
    },
    "telegram": {
        "exe": "Telegram.exe",
        "start": "telegram",
        "aliases": ["telegram"],
    },
    "whatsapp": {
        "exe": "WhatsApp.exe",
        "start": "whatsapp",
        "aliases": ["whatsapp", "whats app"],
    },
    # Microsoft
    "word": {
        "exe": "WINWORD.EXE",
        "start": "winword",
        "aliases": ["word", "microsoft word"],
    },
    "excel": {
        "exe": "EXCEL.EXE",
        "start": "excel",
        "aliases": ["excel", "microsoft excel"],
    },
    "powerpoint": {
        "exe": "POWERPNT.EXE",
        "start": "powerpnt",
        "aliases": ["powerpoint", "power point"],
    },
    # Gelistirici
    "vscode": {
        "exe": "Code.exe",
        "start": "code",
        "aliases": ["vscode", "vs code", "visual studio code", "code"],
    },
    # NOT: terminal/cmd/powershell BILEREK burada yok. Bunlar bir kabuk acar;
    # Whisper'in sessizlik/gurultude "open cmd" gibi bir seyi hallusine
    # etmesi (bilinen bir faster-whisper davranisi) kullaniciyi korkutan,
    # beklenmedik bir komut istemi acilmasina yol acabilirdi. _BLOCKED_EXES
    # asagida hem bu listeye hem bilinmeyen-uygulama yoluna karsi ek koruma.
    # Sistem
    "notepad": {
        "exe": "notepad.exe",
        "start": "notepad",
        "aliases": ["notepad"],
    },
    "calculator": {
        "exe": "calc.exe",
        "start": "calc",
        "aliases": ["calculator", "calc"],
    },
    "explorer": {
        "exe": "explorer.exe",
        "start": "explorer",
        "aliases": ["file explorer", "explorer"],
    },
    "settings": {
        "exe": "ms-settings:",
        "start": "ms-settings:",
        "aliases": ["settings", "windows settings"],
    },
    "task manager": {
        "exe": "taskmgr.exe",
        "start": "taskmgr",
        "aliases": ["task manager", "taskmgr"],
    },
    "paint": {
        "exe": "mspaint.exe",
        "start": "mspaint",
        "aliases": ["paint", "ms paint"],
    },
    # Oyun
    "steam": {
        "exe": "steam.exe",
        "start": "steam",
        "protocol": "steam:",
        "aliases": ["steam"],
    },
    "epic": {
        "exe": "EpicGamesLauncher.exe",
        "start": "com.epicgames.launcher:",
        "aliases": ["epic", "epic games"],
    },
}


def _start_menu_shortcut(name: str) -> Optional[str]:
    """
    Baslat Menusu kisayollari arasinda uygulamayi ara.

    Firefox, Discord, Telegram gibi uygulamalar ne PATH'te ne de "App Paths"
    kaydinda bulunur; kullanicinin profilindeki .lnk dosyasi bunlari acmanin
    tek guvenilir yoludur.
    """
    roots = [
        os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
        os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
    ]
    target = name.lower().strip()
    fallback: Optional[str] = None

    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if not fn.lower().endswith(".lnk"):
                    continue
                stem = os.path.splitext(fn)[0].lower()
                if stem == target:
                    return os.path.join(dirpath, fn)
                # Tam eslesme yoksa "Firefox" ~ "Mozilla Firefox" gibi
                # kismi eslesmeyi yedek olarak sakla
                if fallback is None and target in stem:
                    fallback = os.path.join(dirpath, fn)

    return fallback


def _press_key(vk_code: int) -> None:
    """Simulate a key press and release using Windows API."""
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


# ─── Ses Kontrolu ────────────────────────────────────────────

def volume_up(percentage: int = 10) -> str:
    """Sesi artir (yuzde olarak)."""
    steps = max(1, round(percentage / 2))
    for _ in range(steps):
        _press_key(VK_VOLUME_UP)
    logger.info("Volume up (%d%%, %d steps)", percentage, steps)
    return f"Done, volume up by {percentage}%."


def volume_down(percentage: int = 10) -> str:
    """Sesi azalt (yuzde olarak)."""
    steps = max(1, round(percentage / 2))
    for _ in range(steps):
        _press_key(VK_VOLUME_DOWN)
    logger.info("Volume down (%d%%, %d steps)", percentage, steps)
    return f"Done, volume down by {percentage}%."


def set_volume_absolute(percentage: int) -> str:
    """Sesi mutlak yuzdeye ayarla (0-100) pycaw kullanarak."""
    percentage = max(0, min(100, percentage))
    
    # COM threading modelini initialize et — farkli thread'lerden
    # cagrildiginda CoInitialize yapilmamis olabilir, bu da
    # pycaw/comtypes hatasina yol acar.
    com_initialized = False
    try:
        ctypes.windll.ole32.CoInitialize(None)
        com_initialized = True
    except Exception:
        pass

    try:
        from pycaw.pycaw import AudioUtilities

        devices = AudioUtilities.GetSpeakers()
        volume = devices.EndpointVolume
        
        # SetMasterVolumeLevelScalar takes a float between 0.0 and 1.0
        volume.SetMasterVolumeLevelScalar(percentage / 100.0, None)
        
        logger.info("Set absolute volume to %d%%", percentage)
        return f"Volume set to {percentage}%."
    except ImportError as e:
        logger.error("Volume control dependency missing (pycaw/comtypes): %s", e)
        return "Volume control requires pycaw and comtypes. Please install them."
    except Exception as e:
        logger.error("Failed to set absolute volume: %s", e)
        return f"Sorry, I couldn't set the volume: {e}"
    finally:
        # COM threading modelini temizle
        if com_initialized:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass


def volume_mute() -> str:
    """Sesi kapat/ac (toggle)."""
    _press_key(VK_VOLUME_MUTE)
    logger.info("Volume mute toggled")
    return "Done, mute toggled."


def media_play_pause() -> str:
    """Medya oynat/duraklat."""
    _press_key(VK_MEDIA_PLAY_PAUSE)
    logger.info("Media play/pause")
    return "Done."


def media_next() -> str:
    """Sonraki sarki."""
    _press_key(VK_MEDIA_NEXT)
    logger.info("Media next track")
    return "Next track."


def media_prev() -> str:
    """Onceki sarki."""
    _press_key(VK_MEDIA_PREV)
    logger.info("Media previous track")
    return "Previous track."


def play_on_spotify(song_name: str) -> str:
    """Spotify'da sarki/sanatci arat ve API uzerinden oynat."""
    from core.config import config

    # Ortam degiskeni config.yaml'i ezer — ClaudeEngine ile ayni desen.
    # Boylece gizli anahtarlar diske yazilmadan kullanilabilir.
    client_id = os.environ.get("SPOTIFY_CLIENT_ID") or config.get("spotify", "client_id")
    client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET") or config.get("spotify", "client_secret")
    redirect_uri = config.get("spotify", "redirect_uri", default="http://localhost:8080")

    if not client_id or not client_secret:
        logger.warning("Spotify Client ID/Secret not configured.")
        return "Please configure your Spotify Client ID and Secret in settings."

    try:
        # Lazy load to avoid startup delay if spotipy is missing or not used
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth

        scope = "user-read-playback-state,user-modify-playback-state"
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            open_browser=True,
            # OAuth token'i proje kokune degil, kullanici cache dizinine yaz —
            # yanlislikla repo icinde durmasini engeller.
            cache_path=os.path.join(_user_cache_dir(), "spotify_token.json"),
        )
        
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        # 1. Sarkiyi arat (Populariteye gore siralayarak dogrulugu artir)
        results = sp.search(q=song_name, limit=5, type='track')
        items = results.get('tracks', {}).get('items', [])
        
        if not items:
            return f"I couldn't find '{song_name}' on Spotify."
            
        # Sort by popularity to avoid weird covers
        items.sort(key=lambda x: x.get('popularity', 0), reverse=True)
        best_track = items[0]
            
        track_uri = best_track['uri']
        track_name = best_track['name']
        artist_name = best_track['artists'][0]['name']
        
        # 2. Aktif cihazi bul
        devices = sp.devices()
        active_device = None
        
        for d in devices.get('devices', []):
            if d['is_active']:
                active_device = d['id']
                break
                
        # Eger aktif cihaz yoksa, herhangi bir cihaz
        if not active_device and devices.get('devices'):
            active_device = devices['devices'][0]['id']
            
        # Hic cihaz acik degilse
        if not active_device:
            logger.info("No active Spotify devices. Opening Spotify app.")
            os.startfile(track_uri)
            return f"I couldn't find an active device, but I opened {track_name} for you."
            
        # 3. Oynat
        sp.start_playback(device_id=active_device, uris=[track_uri])
        logger.info("Spotify API play successful: %s by %s", track_name, artist_name)
        return f"Playing {track_name} by {artist_name} on Spotify."
        
    except ImportError:
        logger.error("spotipy module missing")
        return "Spotipy library is missing. Please run pip install spotipy."
    except Exception as e:
        logger.error("Spotify API play failed: %s", e)
        # Hata durumunda sadece arat
        query = urllib.parse.quote(song_name)
        os.startfile(f"spotify:search:{query}")
        return f"There was a connection issue, but I searched for {song_name} on Spotify."


# ─── Uygulama Acma ───────────────────────────────────────────

def open_app(app_name: str) -> str:
    """
    Uygulamayi ac. Bilinen uygulamalar listesinden veya shell aramasiyla.
    
    Args:
        app_name: Uygulamanin adi (kucuk harf, temizlenmis)
    
    Returns:
        Kullaniciya gosterilecek onay mesaji
    """
    app_lower = app_name.lower().strip()

    # Bir kabuk/komut istemi asla sesle acilamaz — Whisper sessizlik veya
    # gurultude "open cmd" gibi bir seyi hallusine edebilir (bilinen bir
    # faster-whisper davranisi) ve beklenmedik bir terminal acilmasi
    # kullaniciyi korkutur. Hem bilinen-uygulama hem bilinmeyen-uygulama
    # yolunu kapsayacak sekilde burada, isim eslesmesinden once kontrol et.
    if app_lower in _BLOCKED_APP_NAMES:
        logger.info("Refused to open a shell via voice/text command: %r", app_name)
        return "Sorry, I can't open a command prompt for security reasons."

    # Bilinen uygulamalar listesinde ara
    for key, info in KNOWN_APPS.items():
        aliases = info.get("aliases", [])
        if app_lower in aliases or app_lower == key:
            return _launch_app(key, info)

    # Bilinmeyen uygulama — once adi dogrula, sonra kabuk olmadan dene
    if not _is_safe_name(app_name):
        logger.warning("Rejected unsafe app name: %r", app_name)
        return f"Sorry, I can't open {app_name}."

    return _launch_unknown(app_name)


def _launch_app(name: str, info: Dict[str, Any]) -> str:
    """Bilinen bir uygulamayi baslat (KNOWN_APPS'ten gelen sabit degerlerle)."""
    try:
        # Protocol varsa (spotify:, steam:, ms-settings:) onu kullan
        target = info.get("protocol") or info.get("start", name)

        # ShellExecute — kabuk (cmd.exe) baslatmadan calisir:
        # hem enjeksiyona kapali hem de bir process daha az.
        os.startfile(target)
        logger.info("Launched %s via ShellExecute: %s", name, target)
        return f"Opening {name}."

    except OSError:
        # PATH ve "App Paths" bulamadi — Baslat Menusu kisayoluna dus
        shortcut = _start_menu_shortcut(name)
        if shortcut:
            try:
                os.startfile(shortcut)
                logger.info("Launched %s via Start Menu shortcut: %s", name, shortcut)
                return f"Opening {name}."
            except Exception as e:
                logger.error("Shortcut launch failed for %s: %s", name, e)
        logger.warning("Could not resolve %s to an executable", name)
        return f"Sorry, I couldn't find {name} on this computer."

    except Exception as e:
        logger.error("Failed to launch %s: %s", name, e)
        return f"Sorry, I couldn't open {name}."


def _launch_unknown(app_name: str) -> str:
    """Bilinmeyen bir uygulamayi ShellExecute ile baslat (kabuk yok)."""
    try:
        # os.startfile PATH ve "App Paths" registry kaydini tarar;
        # bulunamazsa OSError firlatir — bu sayede sessiz basarisizlik olmaz.
        os.startfile(app_name)
        logger.info("Launched unknown app via ShellExecute: %s", app_name)
        return f"Opening {app_name}."
    except OSError:
        shortcut = _start_menu_shortcut(app_name)
        if shortcut:
            try:
                os.startfile(shortcut)
                logger.info("Launched %s via Start Menu shortcut: %s", app_name, shortcut)
                return f"Opening {app_name}."
            except Exception as e:
                logger.error("Shortcut launch failed for %s: %s", app_name, e)
        logger.info("Unknown app not found: %s", app_name)
        return f"Sorry, I couldn't find {app_name} on this computer."
    except Exception as e:
        logger.error("Failed to launch unknown app %s: %s", app_name, e)
        return f"Sorry, I couldn't open {app_name}."


# ─── Uygulama Kapatma ────────────────────────────────────────

def close_app(app_name: str) -> str:
    """Uygulamayi kapat (taskkill ile)."""
    app_lower = app_name.lower().strip()

    # Bilinen uygulamalarda exe adini bul
    exe_name: Optional[str] = None
    for key, info in KNOWN_APPS.items():
        aliases = info.get("aliases", [])
        if app_lower in aliases or app_lower == key:
            exe_name = info.get("exe")
            break

    if not exe_name:
        # Bilinmeyen uygulama — adi dogrula, taskkill'e rastgele metin gecirme
        if not _is_safe_name(app_lower):
            logger.warning("Rejected unsafe app name for close: %r", app_name)
            return f"Sorry, I can't close {app_name}."
        exe_name = f"{app_lower}.exe"

    try:
        subprocess.run(
            ["taskkill", "/IM", exe_name, "/F"],
            capture_output=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        logger.info("Closed app: %s (%s)", app_name, exe_name)
        return f"Closed {app_name}."
    except Exception as e:
        logger.error("Failed to close %s: %s", app_name, e)
        return f"Sorry, I couldn't close {app_name}."


# ─── Sistem Komutlari ────────────────────────────────────────

def lock_screen() -> str:
    """Ekrani kilitle."""
    ctypes.windll.user32.LockWorkStation()
    logger.info("Screen locked")
    return "Locking screen."


def open_url(url: str) -> str:
    """URL'yi varsayilan tarayicida ac."""
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    os.startfile(url)
    logger.info("Opened URL: %s", url)
    return f"Opening {url}."


def web_search(query: str) -> str:
    """Google'da arama yap."""
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    os.startfile(search_url)
    logger.info("Web search: %s", query)
    return f"Searching for {query}."


def screenshot() -> str:
    """Ekran goruntusu al (Snipping Tool)."""
    try:
        os.startfile("ms-screenclip:")
        logger.info("Screenshot tool opened")
        return "Opening screenshot tool."
    except Exception:
        # Eski Windows surumleri icin klasik Snipping Tool
        try:
            os.startfile("snippingtool")
            return "Opening screenshot tool."
        except Exception as e:
            logger.error("Screenshot failed: %s", e)
            return "Sorry, couldn't open screenshot tool."


def minimize_all() -> str:
    """Tum pencereleri simge durumuna kucult."""
    ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)  # Win key down
    ctypes.windll.user32.keybd_event(0x44, 0, 0, 0)  # D key down
    time.sleep(0.05)
    ctypes.windll.user32.keybd_event(0x44, 0, KEYEVENTF_KEYUP, 0)
    ctypes.windll.user32.keybd_event(0x5B, 0, KEYEVENTF_KEYUP, 0)
    logger.info("All windows minimized")
    return "Done, all windows minimized."


# Guc islemleri yanlis duyulmus tek bir komutla tetiklenmemeli:
# once "arm" edilir, kullanici 30 saniye icinde onaylarsa calisir.
_PENDING_POWER_ACTION: Optional[str] = None
_PENDING_POWER_TIME: float = 0.0
_POWER_CONFIRM_WINDOW_S: float = 30.0

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _arm_power_action(action: str, label: str) -> str:
    """Guc islemini onay bekler duruma al."""
    global _PENDING_POWER_ACTION, _PENDING_POWER_TIME
    _PENDING_POWER_ACTION = action
    _PENDING_POWER_TIME = time.time()
    logger.info("Power action armed, awaiting confirmation: %s", action)
    return f"Are you sure you want to {label}? Say confirm to proceed."


def shutdown_pc() -> str:
    """Kapatmayi onaya al (calistirmaz — confirm_power_action calistirir)."""
    return _arm_power_action("shutdown", "shut down the computer")


def restart_pc() -> str:
    """Yeniden baslatmayi onaya al."""
    return _arm_power_action("restart", "restart the computer")


def confirm_power_action() -> str:
    """Bekleyen guc islemini onayla ve 30 saniyelik geri sayimi baslat."""
    global _PENDING_POWER_ACTION

    if _PENDING_POWER_ACTION is None:
        return "There's nothing to confirm."

    if time.time() - _PENDING_POWER_TIME > _POWER_CONFIRM_WINDOW_S:
        _PENDING_POWER_ACTION = None
        return "That confirmation expired. Please ask again."

    action = _PENDING_POWER_ACTION
    _PENDING_POWER_ACTION = None

    flag = "/s" if action == "shutdown" else "/r"
    subprocess.Popen(["shutdown", flag, "/t", "30"], creationflags=_NO_WINDOW)
    logger.info("Power action confirmed and scheduled: %s (30s)", action)
    verb = "Shutting down" if action == "shutdown" else "Restarting"
    return f"{verb} in 30 seconds. Say cancel shutdown to abort."


def cancel_shutdown() -> str:
    """Bekleyen onayi ve zamanlanmis kapatmayi iptal et."""
    global _PENDING_POWER_ACTION
    _PENDING_POWER_ACTION = None
    subprocess.Popen(["shutdown", "/a"], creationflags=_NO_WINDOW)
    logger.info("Shutdown cancelled")
    return "Shutdown cancelled."
