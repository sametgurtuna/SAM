# SAM — System Commands
# Bilgisayar uzerinde direkt islem yapan komutlar:
# uygulama acma/kapatma, ses kontrolu, ekran kilitleme, vb.

import ctypes
import logging
import os
import subprocess
import time
import urllib.parse
from typing import Optional, Dict, Any

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



# ─── Bilinen Uygulamalar ──────────────────────────────────────
# Anahtar: kucultumus isim → (arama_deseni, baslatma_komutu)
# Oncelik: shell start (Windows baslat menusunden bulur) > direkt yol

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
    "terminal": {
        "exe": "wt.exe",
        "start": "wt",
        "aliases": ["terminal", "windows terminal", "command prompt"],
    },
    "cmd": {
        "exe": "cmd.exe",
        "start": "cmd",
        "aliases": ["cmd"],
    },
    "powershell": {
        "exe": "powershell.exe",
        "start": "powershell",
        "aliases": ["powershell", "power shell"],
    },
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
    
    client_id = config.get("spotify", "client_id")
    client_secret = config.get("spotify", "client_secret")
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
            open_browser=True
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

    # Bilinen uygulamalar listesinde ara
    for key, info in KNOWN_APPS.items():
        aliases = info.get("aliases", [])
        if app_lower in aliases or app_lower == key:
            return _launch_app(key, info)

    # Bilinmeyen uygulama — shell ile dene
    return _launch_unknown(app_name)


def _launch_app(name: str, info: Dict[str, Any]) -> str:
    """Bilinen bir uygulamayi baslat."""
    try:
        # Protocol varsa (spotify:, steam:, ms-settings:) onu kullan
        protocol = info.get("protocol")
        if protocol:
            os.startfile(protocol)
            logger.info("Launched %s via protocol: %s", name, protocol)
            return f"Opening {name}."

        # Shell start ile dene (Windows Baslat menusunden bulur)
        start_cmd = info.get("start", name)
        subprocess.Popen(
            f'start "" "{start_cmd}"',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Launched %s via shell: %s", name, start_cmd)
        return f"Opening {name}."

    except Exception as e:
        logger.error("Failed to launch %s: %s", name, e)
        return f"Sorry, I couldn't open {name}."


def _launch_unknown(app_name: str) -> str:
    """Bilinmeyen bir uygulamayi shell aramasiyla baslat."""
    try:
        subprocess.Popen(
            f'start "" "{app_name}"',
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Attempted to launch unknown app: %s", app_name)
        return f"Trying to open {app_name}."
    except Exception as e:
        logger.error("Failed to launch unknown app %s: %s", app_name, e)
        return f"Sorry, I couldn't find {app_name}."


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
        exe_name = f"{app_lower}.exe"

    try:
        subprocess.run(
            ["taskkill", "/IM", exe_name, "/F"],
            capture_output=True,
            timeout=5,
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
        subprocess.Popen("snippingtool", shell=True)
        logger.info("Screenshot tool opened")
        return "Opening screenshot tool."
    except Exception:
        # Windows 11 uses SnippingTool differently
        try:
            subprocess.Popen("explorer ms-screenclip:", shell=True)
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


def shutdown_pc() -> str:
    """Bilgisayari kapat (30 saniye beklemeli)."""
    subprocess.Popen("shutdown /s /t 30", shell=True)
    logger.info("Shutdown initiated (30s)")
    return "Shutting down in 30 seconds. Say cancel shutdown to abort."


def restart_pc() -> str:
    """Bilgisayari yeniden baslat."""
    subprocess.Popen("shutdown /r /t 30", shell=True)
    logger.info("Restart initiated (30s)")
    return "Restarting in 30 seconds. Say cancel shutdown to abort."


def cancel_shutdown() -> str:
    """Kapatma/yeniden baslatma islemini iptal et."""
    subprocess.Popen("shutdown /a", shell=True)
    logger.info("Shutdown cancelled")
    return "Shutdown cancelled."
